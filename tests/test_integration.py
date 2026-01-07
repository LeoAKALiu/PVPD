"""集成测试 - 测试完整的处理流程."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.geometry.corrector import apply_geometric_correction
from src.inference.models import Detection
from src.inference.result_parser import get_detection_stats
from src.visualization.image_stitcher import create_visualization

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def sample_detections() -> list[Detection]:
    """创建示例检测结果."""
    return [
        Detection(bbox=[10.0, 20.0, 50.0, 50.0], confidence=0.8, category_id=0),
        Detection(bbox=[100.0, 150.0, 50.0, 50.0], confidence=0.7, category_id=0),
        Detection(bbox=[200.0, 250.0, 50.0, 50.0], confidence=0.6, category_id=0),
    ]


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """创建示例图像文件."""
    image_path = tmp_path / "test_image.jpg"
    
    # 创建一个简单的测试图像（500x500，蓝色）
    image_array = np.zeros((500, 500, 3), dtype=np.uint8)
    image_array[:, :] = [255, 0, 0]  # BGR 格式：蓝色
    
    import cv2
    
    cv2.imwrite(str(image_path), image_array)
    
    return image_path


class TestEndToEndFlow:
    """测试端到端流程."""
    
    def test_parse_and_visualize(
        self, sample_detections: list[Detection], sample_image: Path
    ) -> None:
        """测试解析和可视化流程."""
        # 获取统计信息
        stats = get_detection_stats(sample_detections)
        
        assert stats["total"] == len(sample_detections)
        assert stats["high_confidence"] >= 0
        assert stats["medium_confidence"] >= 0
        assert stats["low_confidence"] >= 0
        
        # 创建可视化
        vis_image = create_visualization(
            image_path=sample_image,
            detections=sample_detections,
            output_path=None,
        )
        
        assert vis_image is not None
        assert vis_image.shape[0] > 0
        assert vis_image.shape[1] > 0
    
    def test_geometric_correction_flow(
        self, sample_detections: list[Detection]
    ) -> None:
        """测试几何校正流程."""
        image_shape = (500, 500)
        
        # 应用几何校正
        corrected, stats = apply_geometric_correction(
            detections=sample_detections,
            image_shape=image_shape,
            use_ransac=True,
            use_grid_fill=True,
        )
        
        assert len(corrected) >= len(sample_detections)
        assert stats["original_count"] == len(sample_detections)
        assert stats["corrected_count"] == len(corrected)
        
        # 获取校正后的统计信息
        corrected_stats = get_detection_stats(corrected)
        
        assert corrected_stats["total"] == len(corrected)
    
    def test_full_pipeline(
        self, sample_detections: list[Detection], sample_image: Path
    ) -> None:
        """测试完整处理流程."""
        # 1. 获取统计信息
        stats = get_detection_stats(sample_detections)
        
        # 2. 创建可视化
        vis_image = create_visualization(
            image_path=sample_image,
            detections=sample_detections,
            output_path=None,
        )
        
        # 3. 应用几何校正
        image_shape = (500, 500)
        corrected, correction_stats = apply_geometric_correction(
            detections=sample_detections,
            image_shape=image_shape,
            use_ransac=True,
            use_grid_fill=True,
        )
        
        # 4. 创建校正后的可视化
        corrected_vis_image = create_visualization(
            image_path=sample_image,
            detections=corrected,
            output_path=None,
        )
        
        # 验证所有步骤都成功
        assert stats["total"] > 0
        assert vis_image is not None
        assert len(corrected) >= len(sample_detections)
        assert corrected_vis_image is not None
        assert correction_stats["original_count"] == len(sample_detections)
        assert correction_stats["corrected_count"] == len(corrected)


class TestErrorHandling:
    """测试错误处理."""
    
    def test_empty_detections_visualization(self, sample_image: Path) -> None:
        """测试空检测结果的可视化."""
        detections: list[Detection] = []
        
        vis_image = create_visualization(
            image_path=sample_image,
            detections=detections,
            output_path=None,
        )
        
        assert vis_image is not None
    
    def test_empty_detections_correction(self) -> None:
        """测试空检测结果的几何校正."""
        detections: list[Detection] = []
        image_shape = (500, 500)
        
        corrected, stats = apply_geometric_correction(
            detections=detections,
            image_shape=image_shape,
        )
        
        assert len(corrected) == 0
        assert stats["original_count"] == 0
        assert stats["corrected_count"] == 0
    
    def test_single_detection(self, sample_image: Path) -> None:
        """测试单个检测结果."""
        detections = [
            Detection(bbox=[10.0, 20.0, 50.0, 50.0], confidence=0.8, category_id=0)
        ]
        
        stats = get_detection_stats(detections)
        assert stats["total"] == 1
        
        vis_image = create_visualization(
            image_path=sample_image,
            detections=detections,
            output_path=None,
        )
        
        assert vis_image is not None



