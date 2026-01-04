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
    
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        return container.status == "running"
    except NotFound:
        logger.error(f"容器 '{container_name}' 未找到")
        return False
    except DockerException as e:
        logger.error(f"Docker 错误: {e}")
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
    
    # 转换路径为容器内路径
    docker_input_path = config.get_docker_input_path(image_path)
    docker_output_dir = config.DOCKER_OUTPUT_DIR
    
    # 生成输出文件名（基于输入文件名）
    image_stem = image_path.stem
    json_filename = f"{image_stem}.json"
    image_filename = f"{image_stem}_prediction.jpg"  # SAHI 默认输出格式
    
    docker_json_path = f"{docker_output_dir}/{json_filename}"
    docker_image_path = f"{docker_output_dir}/{image_filename}"
    
    # 构建推理命令
    # 注意：这里假设 PV Pile 容器内有 sahi_inference.py 脚本
    # 实际命令可能需要根据 PV Pile 项目的实际结构调整
    cmd = [
        "python",
        "src/inference/sahi_inference.py",  # 可能需要调整路径
        "--weights", weights_path,
        "--source", docker_input_path,
        "--output-dir", docker_output_dir,
        "--slice-height", str(slice_height),
        "--slice-width", str(slice_width),
        "--conf-threshold", str(conf_threshold),
        "--overlap-ratio", str(overlap_ratio),
        "--save-img",
        "--save-json",
    ]
    
    logger.info(f"开始推理: {image_path.name}")
    logger.debug(f"Docker 命令: {' '.join(cmd)}")
    
    start_time = time.time()
    
    try:
        # 使用 Docker API 执行命令
        client = docker.from_env()
        container = client.containers.get(container_name)
        
        # 执行推理命令
        exec_result = container.exec_run(
            cmd,
            workdir="/app",
            timeout=config.DOCKER_TIMEOUT_SECONDS,
        )
        
        if exec_result.exit_code != 0:
            error_output = exec_result.output.decode("utf-8") if exec_result.output else "无错误输出"
            logger.error(f"推理失败，退出码: {exec_result.exit_code}")
            logger.error(f"错误输出: {error_output}")
            raise RuntimeError(
                f"Docker 推理失败 (退出码: {exec_result.exit_code}): {error_output}"
            )
        
        elapsed_time = time.time() - start_time
        logger.info(f"推理完成，耗时: {elapsed_time:.2f} 秒")
        
        # 检查输出文件是否存在
        local_json_path = output_dir / json_filename
        local_image_path = output_dir / image_filename
        
        # 等待文件写入完成（最多等待 5 秒）
        max_wait = 5
        wait_interval = 0.5
        waited = 0
        
        while waited < max_wait:
            if local_json_path.exists() and local_image_path.exists():
                break
            time.sleep(wait_interval)
            waited += wait_interval
        
        if not local_json_path.exists():
            raise FileNotFoundError(
                f"JSON 结果文件未生成: {local_json_path}"
            )
        
        if not local_image_path.exists():
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

