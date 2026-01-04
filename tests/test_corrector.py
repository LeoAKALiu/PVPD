"""测试几何校正模块."""

from typing import TYPE_CHECKING

import numpy as np
import pytest

from src.geometry.corrector import (
    apply_geometric_correction,
    detections_to_sgf_format,
    fill_grid,
    fit_grid_with_ransac,
    sgf_format_to_detections,
)
from src.inference.models import Detection

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


class TestDetectionsToSgfFormat:
    """测试检测结果转换为 SolarGeoFix 格式."""
    
    def test_conversion(self, sample_detections: list[Detection]) -> None:
        """测试格式转换."""
        sgf_data = detections_to_sgf_format(sample_detections)
        
        assert len(sgf_data) == len(sample_detections)
        assert all(isinstance(item, dict) for item in sgf_data)
        
        # 检查第一个检测结果
        first_sgf = sgf_data[0]
        assert "x_center" in first_sgf
        assert "y_center" in first_sgf
        assert "width" in first_sgf
        assert "height" in first_sgf
        assert "confidence" in first_sgf
        
        # 验证中心点计算
        first_det = sample_detections[0]
        assert first_sgf["x_center"] == first_det.x_center
        assert first_sgf["y_center"] == first_det.y_center


class TestSgfFormatToDetections:
    """测试 SolarGeoFix 格式转换为检测结果."""
    
    def test_conversion(self) -> None:
        """测试格式转换."""
        sgf_data = [
            {
                "x_center": 35.0,
                "y_center": 45.0,
                "width": 50.0,
                "height": 50.0,
                "confidence": 0.8,
            },
            {
                "x_center": 125.0,
                "y_center": 175.0,
                "width": 50.0,
                "height": 50.0,
                "confidence": 0.7,
            },
        ]
        
        detections = sgf_format_to_detections(sgf_data, category_id=0)
        
        assert len(detections) == len(sgf_data)
        assert all(isinstance(d, Detection) for d in detections)
        
        # 检查第一个检测结果
        first_det = detections[0]
        assert first_det.x_center == 35.0
        assert first_det.y_center == 45.0
        assert first_det.bbox[2] == 50.0  # width
        assert first_det.bbox[3] == 50.0  # height
        assert first_det.confidence == 0.8


class TestFitGridWithRansac:
    """测试 RANSAC 网格拟合."""
    
    def test_fit_with_sufficient_points(self) -> None:
        """测试有足够点数时的拟合."""
        # 创建一些有规律的点（近似线性）
        x = np.linspace(0, 100, 10)
        y = 2 * x + 5 + np.random.normal(0, 2, 10)  # 线性关系加噪声
        points = np.column_stack([x, y])
        
        model, fitted_points = fit_grid_with_ransac(points, degree=1)
        
        assert model is not None
        assert fitted_points.shape == points.shape
        assert len(fitted_points) == len(points)
    
    def test_fit_with_insufficient_points(self) -> None:
        """测试点数不足时的拟合."""
        points = np.array([[10.0, 20.0], [30.0, 40.0]])  # 只有 2 个点
        
        model, fitted_points = fit_grid_with_ransac(points)
        
        # 点数不足时应该返回 None 和原始点
        assert model is None
        assert np.array_equal(fitted_points, points)
    
    def test_fit_with_empty_points(self) -> None:
        """测试空点数组."""
        points = np.array([]).reshape(0, 2)
        
        model, fitted_points = fit_grid_with_ransac(points)
        
        assert model is None
        assert len(fitted_points) == 0


class TestFillGrid:
    """测试网格填充."""
    
    def test_fill_grid_with_points(self) -> None:
        """测试有现有点时的网格填充."""
        points = np.array([[50.0, 50.0], [150.0, 150.0], [250.0, 250.0]])
        image_shape = (500, 500)
        
        filled_points = fill_grid(points, image_shape, grid_spacing=100.0)
        
        assert len(filled_points) >= len(points)
        assert all(
            (0 <= p[0] < image_shape[1]) and (0 <= p[1] < image_shape[0])
            for p in filled_points
        )
    
    def test_fill_grid_without_points(self) -> None:
        """测试没有现有点时的网格填充."""
        points = np.array([]).reshape(0, 2)
        image_shape = (500, 500)
        
        filled_points = fill_grid(points, image_shape, grid_spacing=100.0)
        
        assert len(filled_points) > 0
        assert all(
            (0 <= p[0] < image_shape[1]) and (0 <= p[1] < image_shape[0])
            for p in filled_points
        )
    
    def test_fill_grid_small_image(self) -> None:
        """测试小图像的网格填充."""
        points = np.array([[10.0, 10.0]])
        image_shape = (50, 50)
        
        filled_points = fill_grid(points, image_shape, grid_spacing=20.0)
        
        assert len(filled_points) >= len(points)
        assert all(
            (0 <= p[0] < image_shape[1]) and (0 <= p[1] < image_shape[0])
            for p in filled_points
        )


class TestApplyGeometricCorrection:
    """测试几何校正."""
    
    def test_correction_with_detections(
        self, sample_detections: list[Detection]
    ) -> None:
        """测试有检测结果时的几何校正."""
        image_shape = (1000, 1000)
        
        corrected, stats = apply_geometric_correction(
            detections=sample_detections,
            image_shape=image_shape,
            use_ransac=True,
            use_grid_fill=True,
        )
        
        assert len(corrected) >= len(sample_detections)
        assert stats["original_count"] == len(sample_detections)
        assert stats["corrected_count"] == len(corrected)
        assert stats["added_count"] >= 0
        assert stats["removed_count"] >= 0
    
    def test_correction_without_ransac(
        self, sample_detections: list[Detection]
    ) -> None:
        """测试不使用 RANSAC 的几何校正."""
        image_shape = (1000, 1000)
        
        corrected, stats = apply_geometric_correction(
            detections=sample_detections,
            image_shape=image_shape,
            use_ransac=False,
            use_grid_fill=True,
        )
        
        assert len(corrected) >= len(sample_detections)
        assert stats["original_count"] == len(sample_detections)
    
    def test_correction_without_grid_fill(
        self, sample_detections: list[Detection]
    ) -> None:
        """测试不使用网格填充的几何校正."""
        image_shape = (1000, 1000)
        
        corrected, stats = apply_geometric_correction(
            detections=sample_detections,
            image_shape=image_shape,
            use_ransac=True,
            use_grid_fill=False,
        )
        
        # 不使用网格填充时，校正后的数量应该接近原始数量
        assert abs(len(corrected) - len(sample_detections)) <= 2
        assert stats["original_count"] == len(sample_detections)
    
    def test_correction_with_empty_detections(self) -> None:
        """测试空检测结果时的几何校正."""
        image_shape = (1000, 1000)
        
        corrected, stats = apply_geometric_correction(
            detections=[],
            image_shape=image_shape,
        )
        
        assert len(corrected) == 0
        assert stats["original_count"] == 0
        assert stats["corrected_count"] == 0
        assert stats["added_count"] == 0
        assert stats["removed_count"] == 0
    
    def test_correction_preserves_detection_info(
        self, sample_detections: list[Detection]
    ) -> None:
        """测试几何校正保留检测信息."""
        image_shape = (1000, 1000)
        
        corrected, stats = apply_geometric_correction(
            detections=sample_detections,
            image_shape=image_shape,
            use_ransac=False,
            use_grid_fill=False,
        )
        
        # 前几个检测应该保留原始信息
        for i in range(min(len(sample_detections), len(corrected))):
            orig = sample_detections[i]
            corr = corrected[i]
            
            assert corr.confidence == orig.confidence
            assert corr.category_id == orig.category_id
            assert corr.bbox[2] == orig.bbox[2]  # width
            assert corr.bbox[3] == orig.bbox[3]  # height

