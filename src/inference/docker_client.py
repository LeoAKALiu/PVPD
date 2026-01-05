"""Docker 推理客户端 - 与 PV Pile Docker 容器交互."""

import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import ContainerError, DockerException, NotFound

import config

# 配置日志
logger = logging.getLogger(__name__)


def check_container_status(container_name: Optional[str] = None) -> bool:
    """
    检查 Docker 容器是否正在运行.
    
    Args:
        container_name: 容器名称，如果为 None 则使用配置文件中的名称
        
    Returns:
        如果容器正在运行返回 True，否则返回 False
    """
    container_name = container_name or config.CONTAINER_NAME
    
    # 首先尝试使用 Docker API
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        return container.status == "running"
    except NotFound:
        logger.warning(f"容器 '{container_name}' 未找到（Docker API）")
    except DockerException as e:
        logger.warning(f"Docker API 错误: {e}，尝试使用命令行检查")
    except Exception as e:
        logger.warning(f"Docker 连接错误: {e}，尝试使用命令行检查")
    
    # 如果 Docker API 失败，尝试使用命令行作为备用方案
    try:
        import subprocess
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            status = result.stdout.strip()
            is_running = "Up" in status
            if is_running:
                logger.info(f"使用命令行检查：容器 '{container_name}' 正在运行")
            return is_running
    except Exception as e:
        logger.warning(f"命令行检查也失败: {e}")
    
    return False


def run_docker_inference(
    image_path: Path,
    output_dir: Path,
    slice_height: int = config.DEFAULT_SLICE_HEIGHT,
    slice_width: int = config.DEFAULT_SLICE_WIDTH,
    conf_threshold: float = config.DEFAULT_CONF_THRESHOLD,
    overlap_ratio: float = config.DEFAULT_OVERLAP_RATIO,
    weights_path: Optional[str] = None,
    container_name: Optional[str] = None,
) -> dict[str, Any]:
    """
    调用 Docker 容器运行推理.
    
    Args:
        image_path: 输入图像路径（本地路径）
        output_dir: 输出目录（本地路径）
        slice_height: SAHI 切片高度
        slice_width: SAHI 切片宽度
        conf_threshold: 置信度阈值
        overlap_ratio: 重叠比例
        weights_path: 模型权重路径（容器内路径），如果为 None 则使用配置文件中的路径
        container_name: 容器名称，如果为 None 则使用配置文件中的名称
        
    Returns:
        包含以下键的字典:
        - 'json_path': JSON 结果文件路径（本地路径）
        - 'image_path': 标注图像路径（本地路径）
        - 'stats': 统计信息字典
        
    Raises:
        FileNotFoundError: 如果输入图像不存在
        RuntimeError: 如果容器未运行或推理失败
        ValueError: 如果参数无效
    """
    # 参数验证
    if not image_path.exists():
        raise FileNotFoundError(f"输入图像不存在: {image_path}")
    
    if not image_path.suffix.lower() in config.ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(f"不支持的图像格式: {image_path.suffix}")
    
    container_name = container_name or config.CONTAINER_NAME
    weights_path = weights_path or config.MODEL_WEIGHTS
    
    # 检查容器状态
    if not check_container_status(container_name):
        raise RuntimeError(
            f"容器 '{container_name}' 未运行。请先启动容器。"
        )
    
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查并复制文件到容器挂载的输入目录
    mounted_input_dir = config.get_mounted_input_dir()
    if mounted_input_dir and mounted_input_dir.exists():
        # 如果找到了挂载目录，复制文件到那里
        mounted_input_dir.mkdir(parents=True, exist_ok=True)
        target_path = mounted_input_dir / image_path.name
        
        # 如果文件不在挂载目录中，复制它
        if not target_path.exists() or target_path.stat().st_mtime < image_path.stat().st_mtime:
            import shutil
            shutil.copy2(image_path, target_path)
            logger.info(f"已复制文件到挂载目录: {target_path}")
        
        # 使用挂载目录中的文件路径
        docker_input_path = str(Path(config.DOCKER_INPUT_DIR) / image_path.name)
    else:
        # 如果找不到挂载目录，使用原始路径转换
        logger.warning("未找到容器挂载的输入目录，使用原始路径")
        docker_input_path = config.get_docker_input_path(image_path)
    
    docker_output_dir = config.DOCKER_OUTPUT_DIR
    
    # 生成输出文件名（基于输入文件名）
    image_stem = image_path.stem
    json_filename = f"{image_stem}.json"
    image_filename = f"{image_stem}_prediction.jpg"  # SAHI 默认输出格式
    
    docker_json_path = f"{docker_output_dir}/{json_filename}"
    docker_image_path = f"{docker_output_dir}/{image_filename}"
    
    # 构建推理命令
    # 注意：根据 sahi_inference.py 的实际参数名称调整
    cmd = [
        "python",
        "src/inference/sahi_inference.py",  # 可能需要调整路径
        "--weights", weights_path,
        "--source", docker_input_path,
        "--output-dir", docker_output_dir,
        "--slice-height", str(slice_height),
        "--slice-width", str(slice_width),
        "--conf", str(conf_threshold),  # 使用 --conf 而不是 --conf-threshold
        "--overlap-height-ratio", str(overlap_ratio),  # 使用 --overlap-height-ratio
        "--overlap-width-ratio", str(overlap_ratio),  # 使用 --overlap-width-ratio
        "--save-img",
        "--save-json",
    ]
    
    logger.info(f"开始推理: {image_path.name}")
    logger.debug(f"Docker 命令: {' '.join(cmd)}")
    
    # 计算动态超时时间（根据图像大小和切片参数）
    try:
        import cv2
        img = cv2.imread(str(image_path))
        if img is not None:
            img_height, img_width = img.shape[:2]
            # 计算切片数量（考虑重叠）
            effective_slice_height = slice_height * (1 - overlap_ratio)
            effective_slice_width = slice_width * (1 - overlap_ratio)
            num_slices_h = max(1, int((img_height - slice_height) / effective_slice_height) + 1)
            num_slices_w = max(1, int((img_width - slice_width) / effective_slice_width) + 1)
            total_slices = num_slices_h * num_slices_w
            
            # 估算推理时间：每个切片约 0.1-0.5 秒（取决于硬件）
            # 保守估计：每个切片 0.3 秒，加上 50% 的缓冲
            estimated_time = total_slices * 0.3 * 1.5
            
            # 超时时间：估算时间的 2 倍，但不超过最大超时时间
            dynamic_timeout = min(
                max(int(estimated_time * 2), config.DOCKER_TIMEOUT_SECONDS),
                config.DOCKER_TIMEOUT_MAX_SECONDS
            )
            
            logger.info(
                f"图像尺寸: {img_width}x{img_height}, "
                f"切片数: {total_slices}, "
                f"估算时间: {estimated_time:.1f}秒, "
                f"超时设置: {dynamic_timeout}秒"
            )
        else:
            dynamic_timeout = config.DOCKER_TIMEOUT_SECONDS
            logger.warning(f"无法读取图像尺寸，使用默认超时: {dynamic_timeout}秒")
    except Exception as e:
        dynamic_timeout = config.DOCKER_TIMEOUT_SECONDS
        logger.warning(f"计算动态超时失败: {e}，使用默认超时: {dynamic_timeout}秒")
    
    start_time = time.time()
    
    # 尝试使用 Docker API，如果失败则使用命令行
    use_api = True
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        logger.debug("使用 Docker API 执行推理")
    except Exception as e:
        logger.warning(f"Docker API 不可用: {e}，将使用命令行方式")
        use_api = False
    
    try:
        if use_api:
            # 使用 Docker API 执行命令
            exec_result = container.exec_run(
                cmd,
                workdir="/app",
                timeout=dynamic_timeout,
            )
            
            exit_code = exec_result.exit_code
            output = exec_result.output.decode("utf-8") if exec_result.output else ""
        else:
            # 使用命令行作为备用方案
            import subprocess
            import shlex
            
            # 构建完整的 docker exec 命令
            docker_cmd = ["docker", "exec", "-w", "/app", container_name] + cmd
            logger.debug(f"执行命令: {' '.join(shlex.quote(str(c)) for c in docker_cmd)}")
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=dynamic_timeout,
            )
            
            exit_code = result.returncode
            output = result.stdout + result.stderr
        
        if exit_code != 0:
            error_output = output if output else "无错误输出"
            logger.error(f"推理失败，退出码: {exit_code}")
            logger.error(f"错误输出: {error_output}")
            raise RuntimeError(
                f"Docker 推理失败 (退出码: {exit_code}): {error_output}"
            )
        
        elapsed_time = time.time() - start_time
        logger.info(f"推理完成，耗时: {elapsed_time:.2f} 秒")
        
        # 检查输出文件位置
        # 首先检查挂载的输出目录
        mounted_output_dir = config.get_mounted_output_dir()
        if mounted_output_dir and mounted_output_dir.exists():
            # 文件应该在挂载目录中
            mounted_json_path = mounted_output_dir / json_filename
            mounted_image_path = mounted_output_dir / image_filename
            
            # 等待文件写入完成（最多等待 10 秒）
            max_wait = 10
            wait_interval = 0.5
            waited = 0
            
            while waited < max_wait:
                if mounted_json_path.exists():
                    break
                time.sleep(wait_interval)
                waited += wait_interval
            
            if mounted_json_path.exists():
                # 复制文件到本地输出目录（如果不同）
                local_json_path = output_dir / json_filename
                local_image_path = output_dir / image_filename
                
                if mounted_output_dir != output_dir:
                    import shutil
                    shutil.copy2(mounted_json_path, local_json_path)
                    logger.info(f"已复制 JSON 文件到: {local_json_path}")
                    
                    if mounted_image_path.exists():
                        # 注意：图像文件可能是 PNG 而不是 JPG
                        # 尝试查找 PNG 文件
                        png_filename = f"{image_stem}.png"
                        mounted_png_path = mounted_output_dir / png_filename
                        if mounted_png_path.exists():
                            shutil.copy2(mounted_png_path, local_image_path.with_suffix('.png'))
                            local_image_path = local_image_path.with_suffix('.png')
                            logger.info(f"已复制图像文件到: {local_image_path}")
                        elif mounted_image_path.exists():
                            shutil.copy2(mounted_image_path, local_image_path)
                            logger.info(f"已复制图像文件到: {local_image_path}")
                else:
                    local_json_path = mounted_json_path
                    local_image_path = mounted_image_path if mounted_image_path.exists() else None
            else:
                raise FileNotFoundError(
                    f"JSON 结果文件未生成: {mounted_json_path}"
                )
        else:
            # 使用本地输出目录
            local_json_path = output_dir / json_filename
            local_image_path = output_dir / image_filename
            
            # 等待文件写入完成（最多等待 10 秒）
            max_wait = 10
            wait_interval = 0.5
            waited = 0
            
            while waited < max_wait:
                if local_json_path.exists():
                    break
                time.sleep(wait_interval)
                waited += wait_interval
            
            if not local_json_path.exists():
                raise FileNotFoundError(
                    f"JSON 结果文件未生成: {local_json_path}"
                )
            
            if not local_image_path.exists():
                # 尝试查找 PNG 文件
                png_path = output_dir / f"{image_stem}.png"
                if png_path.exists():
                    local_image_path = png_path
                else:
                    logger.warning(f"标注图像未生成: {local_image_path}")
                    local_image_path = None
        
        # 返回结果
        result = {
            "json_path": str(local_json_path),
            "image_path": str(local_image_path) if local_image_path else None,
            "stats": {
                "elapsed_time": elapsed_time,
                "input_file": str(image_path),
                "output_dir": str(output_dir),
            },
        }
        
        return result
        
    except ContainerError as e:
        logger.error(f"容器错误: {e}")
        raise RuntimeError(f"Docker 容器执行错误: {e}") from e
    except DockerException as e:
        logger.error(f"Docker API 错误: {e}")
        raise RuntimeError(f"Docker API 错误: {e}") from e
    except Exception as e:
        logger.error(f"推理过程中发生未知错误: {e}")
        raise RuntimeError(f"推理失败: {e}") from e


def get_container_logs(
    container_name: Optional[str] = None,
    tail: int = 100,
) -> str:
    """
    获取容器日志.
    
    Args:
        container_name: 容器名称，如果为 None 则使用配置文件中的名称
        tail: 返回最后 N 行日志
        
    Returns:
        日志内容字符串
    """
    container_name = container_name or config.CONTAINER_NAME
    
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        logs = container.logs(tail=tail).decode("utf-8")
        return logs
    except Exception as e:
        logger.error(f"获取容器日志失败: {e}")
        return f"无法获取日志: {e}"

