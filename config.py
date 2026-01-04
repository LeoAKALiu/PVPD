"""配置文件 - 管理应用的所有配置项."""

import os
from pathlib import Path
from typing import Optional

# ==================== Docker 配置 ====================
CONTAINER_NAME: str = os.getenv("PV_PILE_CONTAINER_NAME", "pv_pile_detection")
DOCKER_IMAGE: str = os.getenv("PV_PILE_DOCKER_IMAGE", "pv_pile:latest")

# ==================== 模型配置 ====================
# 模型文件路径配置
# 如果当前目录有 best.pt，使用它（需要确保 Docker 容器能访问）
# 否则使用容器内的默认路径
_local_model = Path(__file__).parent / "best.pt"
if _local_model.exists():
    # 如果本地有模型文件，假设它会被挂载到容器的 /app/models/best.pt
    # 或者使用环境变量指定的路径
    MODEL_WEIGHTS: str = os.getenv(
        "PV_PILE_MODEL_WEIGHTS",
        "/app/models/best.pt"  # Docker 容器内的路径
    )
    LOCAL_MODEL_PATH: Path = _local_model  # 本地路径，用于挂载
else:
    MODEL_WEIGHTS: str = os.getenv(
        "PV_PILE_MODEL_WEIGHTS",
        "/app/runs/detect/train4/weights/best.pt"
    )
    LOCAL_MODEL_PATH: Optional[Path] = None

# ==================== 推理参数 ====================
DEFAULT_SLICE_HEIGHT: int = int(os.getenv("PV_PILE_SLICE_HEIGHT", "640"))
DEFAULT_SLICE_WIDTH: int = int(os.getenv("PV_PILE_SLICE_WIDTH", "640"))
DEFAULT_CONF_THRESHOLD: float = float(os.getenv("PV_PILE_CONF_THRESHOLD", "0.25"))
DEFAULT_OVERLAP_RATIO: float = float(os.getenv("PV_PILE_OVERLAP_RATIO", "0.2"))

# ==================== 置信度颜色阈值 ====================
HIGH_CONF_THRESHOLD: float = 0.7    # 绿色
MEDIUM_CONF_THRESHOLD: float = 0.4   # 黄色
LOW_CONF_THRESHOLD: float = 0.0      # 红色

# ==================== 路径配置 ====================
# 项目根目录
PROJECT_ROOT: Path = Path(__file__).parent

# 输入/输出目录
INPUT_DIR: Path = PROJECT_ROOT / "input"
OUTPUT_DIR: Path = PROJECT_ROOT / "output"

# Docker 容器内的路径映射
DOCKER_INPUT_DIR: str = "/app/input"
DOCKER_OUTPUT_DIR: str = "/app/output"

# ==================== 文件配置 ====================
ALLOWED_IMAGE_EXTENSIONS: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG")
MAX_IMAGE_SIZE_MB: int = 100  # 最大图像大小（MB）

# ==================== UI 配置 ====================
STREAMLIT_PAGE_TITLE: str = "PV Pile Integration System"
STREAMLIT_PAGE_ICON: str = "🔋"

# ==================== 性能配置 ====================
DOCKER_TIMEOUT_SECONDS: int = 600  # Docker 命令超时时间（10分钟）
MAX_WORKERS: int = 4  # 最大并发工作线程数

# ==================== 日志配置 ====================
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR: Path = PROJECT_ROOT / "logs"

# ==================== 辅助函数 ====================
def ensure_directories() -> None:
    """确保必要的目录存在."""
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)


def get_docker_input_path(local_path: Path) -> str:
    """
    将本地路径转换为 Docker 容器内的输入路径.
    
    Args:
        local_path: 本地文件路径
        
    Returns:
        Docker 容器内的路径
    """
    try:
        relative_path = local_path.relative_to(INPUT_DIR)
        return str(Path(DOCKER_INPUT_DIR) / relative_path)
    except ValueError:
        # 如果路径不在 INPUT_DIR 下，使用文件名
        return str(Path(DOCKER_INPUT_DIR) / local_path.name)


def get_docker_output_path(local_path: Path) -> str:
    """
    将本地路径转换为 Docker 容器内的输出路径.
    
    Args:
        local_path: 本地文件路径
        
    Returns:
        Docker 容器内的路径
    """
    relative_path = local_path.relative_to(OUTPUT_DIR)
    return str(Path(DOCKER_OUTPUT_DIR) / relative_path)

