"""置信度颜色映射 - 根据置信度返回对应的颜色."""

from typing import Tuple

import config


def get_confidence_color(confidence: float) -> str:
    """
    根据置信度返回颜色名称.
    
    Args:
        confidence: 置信度分数 (0.0-1.0)
        
    Returns:
        颜色名称: 'green' (高), 'yellow' (中), 'red' (低)
    """
    if confidence >= config.HIGH_CONF_THRESHOLD:
        return "green"
    elif confidence >= config.MEDIUM_CONF_THRESHOLD:
        return "yellow"
    else:
        return "red"


def get_confidence_color_rgb(confidence: float) -> Tuple[int, int, int]:
    """
    根据置信度返回 RGB 颜色值.
    
    Args:
        confidence: 置信度分数 (0.0-1.0)
        
    Returns:
        RGB 颜色元组 (R, G, B)，值范围 0-255
    """
    if confidence >= config.HIGH_CONF_THRESHOLD:
        return (0, 255, 0)  # 绿色
    elif confidence >= config.MEDIUM_CONF_THRESHOLD:
        return (255, 255, 0)  # 黄色
    else:
        return (255, 0, 0)  # 红色


def get_confidence_color_bgr(confidence: float) -> Tuple[int, int, int]:
    """
    根据置信度返回 BGR 颜色值（OpenCV 格式）.
    
    Args:
        confidence: 置信度分数 (0.0-1.0)
        
    Returns:
        BGR 颜色元组 (B, G, R)，值范围 0-255
    """
    rgb = get_confidence_color_rgb(confidence)
    return (rgb[2], rgb[1], rgb[0])  # 转换为 BGR


def get_confidence_label(confidence: float) -> str:
    """
    根据置信度返回标签文本.
    
    Args:
        confidence: 置信度分数 (0.0-1.0)
        
    Returns:
        标签文本: '高置信度', '中置信度', '低置信度'
    """
    if confidence >= config.HIGH_CONF_THRESHOLD:
        return "高置信度"
    elif confidence >= config.MEDIUM_CONF_THRESHOLD:
        return "中置信度"
    else:
        return "低置信度"


def get_confidence_emoji(confidence: float) -> str:
    """
    根据置信度返回表情符号.
    
    Args:
        confidence: 置信度分数 (0.0-1.0)
        
    Returns:
        表情符号: 🟢 (高), 🟡 (中), 🔴 (低)
    """
    if confidence >= config.HIGH_CONF_THRESHOLD:
        return "🟢"
    elif confidence >= config.MEDIUM_CONF_THRESHOLD:
        return "🟡"
    else:
        return "🔴"



