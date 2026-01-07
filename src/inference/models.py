"""数据模型 - 定义检测结果的数据结构."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Detection:
    """
    检测结果数据类.
    
    Attributes:
        bbox: 边界框坐标 [x, y, width, height] (COCO 格式)
        confidence: 置信度分数 (0.0-1.0)
        category_id: 类别 ID
        category_name: 类别名称（可选）
        x_center: 中心点 x 坐标（可选，用于几何校正）
        y_center: 中心点 y 坐标（可选，用于几何校正）
    """
    
    bbox: list[float]  # [x, y, width, height]
    confidence: float
    category_id: int
    category_name: Optional[str] = None
    x_center: Optional[float] = None
    y_center: Optional[float] = None
    
    def __post_init__(self) -> None:
        """初始化后处理，计算中心点坐标."""
        if self.x_center is None or self.y_center is None:
            self.x_center = self.bbox[0] + self.bbox[2] / 2.0
            self.y_center = self.bbox[1] + self.bbox[3] / 2.0
    
    def to_dict(self) -> dict:
        """
        转换为字典格式.
        
        Returns:
            包含所有字段的字典
        """
        return {
            "bbox": self.bbox,
            "confidence": self.confidence,
            "category_id": self.category_id,
            "category_name": self.category_name,
            "x_center": self.x_center,
            "y_center": self.y_center,
        }
    
    def to_sgf_format(self) -> dict:
        """
        转换为 SolarGeoFix 格式.
        
        Returns:
            SolarGeoFix 格式的字典
        """
        return {
            "x_center": self.x_center or (self.bbox[0] + self.bbox[2] / 2.0),
            "y_center": self.y_center or (self.bbox[1] + self.bbox[3] / 2.0),
            "width": self.bbox[2],
            "height": self.bbox[3],
            "confidence": self.confidence,
        }



