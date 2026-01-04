"""结果解析模块 - 解析 SAHI JSON 结果."""

import json
import logging
from pathlib import Path
from typing import Any

from src.inference.models import Detection

# 配置日志
logger = logging.getLogger(__name__)


def parse_sahi_results(json_path: Path | str) -> list[Detection]:
    """
    解析 SAHI JSON 结果文件.
    
    Args:
        json_path: JSON 结果文件路径
        
    Returns:
        检测结果列表
        
    Raises:
        FileNotFoundError: 如果 JSON 文件不存在
        ValueError: 如果 JSON 格式无效
        KeyError: 如果 JSON 缺少必需的字段
    """
    json_path = Path(json_path)
    
    if not json_path.exists():
        raise FileNotFoundError(f"JSON 文件不存在: {json_path}")
    
    logger.info(f"解析 JSON 结果: {json_path}")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"无效的 JSON 格式: {e}") from e
    except Exception as e:
        raise ValueError(f"读取 JSON 文件失败: {e}") from e
    
    # 验证 JSON 结构并处理不同格式
    # 支持两种格式：
    # 1. COCO 格式: {"annotations": [...]}
    # 2. 列表格式: [...]
    if isinstance(data, list):
        # 如果根对象是列表，直接使用
        annotations = data
        logger.debug("检测到列表格式 JSON")
    elif isinstance(data, dict):
        # 如果是字典，尝试提取 annotations
        if "annotations" not in data:
            raise KeyError("JSON 缺少 'annotations' 字段")
        annotations = data["annotations"]
        if not isinstance(annotations, list):
            raise ValueError("'annotations' 必须是列表")
        logger.debug("检测到 COCO 格式 JSON")
    else:
        raise ValueError(f"不支持的 JSON 格式: 根对象类型为 {type(data)}")
    
    # 解析检测结果
    detections: list[Detection] = []
    
    for idx, ann in enumerate(annotations):
        try:
            # 提取必需字段
            bbox = ann.get("bbox")
            score = ann.get("score")
            category_id = ann.get("category_id")
            
            if bbox is None:
                logger.warning(f"注释 {idx} 缺少 'bbox' 字段，跳过")
                continue
            
            if score is None:
                logger.warning(f"注释 {idx} 缺少 'score' 字段，跳过")
                continue
            
            if category_id is None:
                logger.warning(f"注释 {idx} 缺少 'category_id' 字段，跳过")
                continue
            
            # 验证 bbox 格式
            if not isinstance(bbox, list) or len(bbox) != 4:
                logger.warning(f"注释 {idx} 的 'bbox' 格式无效，跳过")
                continue
            
            # 验证数据类型
            try:
                bbox_float = [float(x) for x in bbox]
                score_float = float(score)
                category_id_int = int(category_id)
            except (ValueError, TypeError) as e:
                logger.warning(f"注释 {idx} 数据类型转换失败: {e}，跳过")
                continue
            
            # 验证置信度范围
            if not 0.0 <= score_float <= 1.0:
                logger.warning(
                    f"注释 {idx} 的置信度超出范围 [0.0, 1.0]: {score_float}，跳过"
                )
                continue
            
            # 创建 Detection 对象
            detection = Detection(
                bbox=bbox_float,
                confidence=score_float,
                category_id=category_id_int,
                category_name=ann.get("category_name"),
            )
            
            detections.append(detection)
            
        except Exception as e:
            logger.warning(f"解析注释 {idx} 时出错: {e}，跳过")
            continue
    
    logger.info(f"成功解析 {len(detections)} 个检测结果")
    
    return detections


def get_detection_stats(detections: list[Detection]) -> dict[str, Any]:
    """
    获取检测结果统计信息.
    
    Args:
        detections: 检测结果列表
        
    Returns:
        包含统计信息的字典
    """
    if not detections:
        return {
            "total": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "avg_confidence": 0.0,
            "categories": {},
        }
    
    import config
    
    high_conf = sum(
        1 for d in detections if d.confidence >= config.HIGH_CONF_THRESHOLD
    )
    medium_conf = sum(
        1
        for d in detections
        if config.MEDIUM_CONF_THRESHOLD
        <= d.confidence
        < config.HIGH_CONF_THRESHOLD
    )
    low_conf = sum(
        1 for d in detections if d.confidence < config.MEDIUM_CONF_THRESHOLD
    )
    
    avg_confidence = sum(d.confidence for d in detections) / len(detections)
    
    # 统计类别
    categories: dict[int, int] = {}
    for d in detections:
        categories[d.category_id] = categories.get(d.category_id, 0) + 1
    
    return {
        "total": len(detections),
        "high_confidence": high_conf,
        "medium_confidence": medium_conf,
        "low_confidence": low_conf,
        "avg_confidence": avg_confidence,
        "categories": categories,
    }

