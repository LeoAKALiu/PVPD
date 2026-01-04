"""图像拼合模块 - 在原图上绘制检测框."""

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

from src.inference.models import Detection
from src.visualization.confidence_colors import get_confidence_color_bgr

# 配置日志
logger = logging.getLogger(__name__)


def draw_detection_on_image(
    image: np.ndarray,
    detection: Detection,
    color: Optional[tuple[int, int, int]] = None,
    thickness: int = 2,
    show_label: bool = True,
    show_confidence: bool = True,
) -> np.ndarray:
    """
    在图像上绘制单个检测框.
    
    Args:
        image: 输入图像（numpy 数组，BGR 格式）
        detection: 检测结果
        color: 颜色 (B, G, R)，如果为 None 则根据置信度自动选择
        thickness: 线条粗细
        show_label: 是否显示标签
        show_confidence: 是否显示置信度
        
    Returns:
        绘制后的图像（numpy 数组）
    """
    if color is None:
        color = get_confidence_color_bgr(detection.confidence)
    
    # 提取边界框坐标
    x, y, w, h = detection.bbox
    x, y, w, h = int(x), int(y), int(w), int(h)
    
    # 绘制矩形框
    cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
    
    # 准备标签文本
    if show_label or show_confidence:
        label_parts = []
        
        if show_label and detection.category_name:
            label_parts.append(detection.category_name)
        elif show_label:
            label_parts.append(f"Class {detection.category_id}")
        
        if show_confidence:
            label_parts.append(f"{detection.confidence:.2f}")
        
        if label_parts:
            label = " ".join(label_parts)
            
            # 计算文本大小
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            text_thickness = 1
            (text_width, text_height), baseline = cv2.getTextSize(
                label, font, font_scale, text_thickness
            )
            
            # 绘制文本背景
            text_x = x
            text_y = y - 5 if y - 5 > text_height else y + text_height + 5
            
            cv2.rectangle(
                image,
                (text_x, text_y - text_height - baseline),
                (text_x + text_width, text_y + baseline),
                color,
                -1,
            )
            
            # 绘制文本
            text_color = (255, 255, 255)  # 白色文本
            cv2.putText(
                image,
                label,
                (text_x, text_y),
                font,
                font_scale,
                text_color,
                text_thickness,
                cv2.LINE_AA,
            )
    
    return image


def draw_detections_on_image(
    image: np.ndarray,
    detections: list[Detection],
    thickness: int = 2,
    show_label: bool = True,
    show_confidence: bool = True,
) -> np.ndarray:
    """
    在图像上绘制多个检测框.
    
    Args:
        image: 输入图像（numpy 数组，BGR 格式）
        detections: 检测结果列表
        thickness: 线条粗细
        show_label: 是否显示标签
        show_confidence: 是否显示置信度
        
    Returns:
        绘制后的图像（numpy 数组）
    """
    # 创建图像副本，避免修改原图
    result_image = image.copy()
    
    for detection in detections:
        result_image = draw_detection_on_image(
            result_image,
            detection,
            thickness=thickness,
            show_label=show_label,
            show_confidence=show_confidence,
        )
    
    return result_image


def load_image(image_path: Path | str) -> np.ndarray:
    """
    加载图像文件.
    
    Args:
        image_path: 图像文件路径
        
    Returns:
        图像数组（BGR 格式）
        
    Raises:
        FileNotFoundError: 如果图像文件不存在
        ValueError: 如果图像格式不支持
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"图像文件不存在: {image_path}")
    
    # 使用 OpenCV 加载图像（BGR 格式）
    image = cv2.imread(str(image_path))
    
    if image is None:
        raise ValueError(f"无法加载图像: {image_path}")
    
    logger.info(f"成功加载图像: {image_path} (尺寸: {image.shape})")
    
    return image


def save_image(image: np.ndarray, output_path: Path | str) -> None:
    """
    保存图像文件.
    
    Args:
        image: 图像数组（BGR 格式）
        output_path: 输出文件路径
        
    Raises:
        ValueError: 如果保存失败
    """
    output_path = Path(output_path)
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 使用 OpenCV 保存图像
    success = cv2.imwrite(str(output_path), image)
    
    if not success:
        raise ValueError(f"保存图像失败: {output_path}")
    
    logger.info(f"成功保存图像: {output_path}")


def create_visualization(
    image_path: Path | str,
    detections: list[Detection],
    output_path: Optional[Path | str] = None,
    thickness: int = 2,
    show_label: bool = True,
    show_confidence: bool = True,
) -> np.ndarray:
    """
    创建可视化图像（加载图像、绘制检测框、可选保存）.
    
    Args:
        image_path: 输入图像路径
        detections: 检测结果列表
        output_path: 输出图像路径（可选）
        thickness: 线条粗细
        show_label: 是否显示标签
        show_confidence: 是否显示置信度
        
    Returns:
        可视化后的图像（numpy 数组）
    """
    # 加载图像
    image = load_image(image_path)
    
    # 绘制检测框
    vis_image = draw_detections_on_image(
        image,
        detections,
        thickness=thickness,
        show_label=show_label,
        show_confidence=show_confidence,
    )
    
    # 保存图像（如果指定了输出路径）
    if output_path is not None:
        save_image(vis_image, output_path)
    
    return vis_image


def image_to_pil(image: np.ndarray) -> Image.Image:
    """
    将 OpenCV 图像（BGR）转换为 PIL 图像（RGB）.
    
    Args:
        image: OpenCV 图像数组（BGR 格式）
        
    Returns:
        PIL 图像对象（RGB 格式）
    """
    # OpenCV 使用 BGR，PIL 使用 RGB
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_image)


def pil_to_image(pil_image: Image.Image) -> np.ndarray:
    """
    将 PIL 图像（RGB）转换为 OpenCV 图像（BGR）.
    
    Args:
        pil_image: PIL 图像对象（RGB 格式）
        
    Returns:
        OpenCV 图像数组（BGR 格式）
    """
    # PIL 使用 RGB，OpenCV 使用 BGR
    rgb_array = np.array(pil_image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)
    return bgr_array

