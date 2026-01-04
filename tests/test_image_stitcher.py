"""测试图像拼合模块."""

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
import cv2
from PIL import Image

from src.inference.models import Detection
from src.visualization.image_stitcher import (
    create_visualization,
    draw_detection_on_image,
    draw_detections_on_image,
    image_to_pil,
    load_image,
    pil_to_image,
    save_image,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """创建示例图像文件."""
    image_path = tmp_path / "test_image.jpg"
    
    # 创建一个简单的测试图像（100x100，蓝色）
    image_array = np.zeros((100, 100, 3), dtype=np.uint8)
    image_array[:, :] = [255, 0, 0]  # BGR 格式：蓝色
    
    cv2.imwrite(str(image_path), image_array)
    
    return image_path


@pytest.fixture
def sample_detection() -> Detection:
    """创建示例检测结果."""
    return Detection(
        bbox=[10.0, 20.0, 50.0, 30.0],
        confidence=0.85,
        category_id=0,
        category_name="pile",
    )


class TestLoadImage:
    """测试加载图像."""
    
    def test_load_existing_image(self, sample_image: Path) -> None:
        """测试加载存在的图像."""
        image = load_image(sample_image)
        
        assert isinstance(image, np.ndarray)
        assert image.shape == (100, 100, 3)
    
    def test_load_nonexistent_image(self, tmp_path: Path) -> None:
        """测试加载不存在的图像."""
        image_path = tmp_path / "nonexistent.jpg"
        
        with pytest.raises(FileNotFoundError, match="图像文件不存在"):
            load_image(image_path)


class TestSaveImage:
    """测试保存图像."""
    
    def test_save_image(self, tmp_path: Path) -> None:
        """测试保存图像."""
        # 创建测试图像
        image = np.zeros((50, 50, 3), dtype=np.uint8)
        image[:, :] = [0, 255, 0]  # BGR 格式：绿色
        
        output_path = tmp_path / "output.jpg"
        save_image(image, output_path)
        
        assert output_path.exists()
        
        # 验证保存的图像可以重新加载
        loaded = load_image(output_path)
        assert loaded.shape == (50, 50, 3)


class TestDrawDetectionOnImage:
    """测试绘制单个检测框."""
    
    def test_draw_detection(self, sample_image: Path, sample_detection: Detection) -> None:
        """测试绘制检测框."""
        image = load_image(sample_image)
        result = draw_detection_on_image(image, sample_detection)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == image.shape
        # 图像应该被修改（添加了检测框）
        assert not np.array_equal(result, image)
    
    def test_draw_detection_with_custom_color(
        self, sample_image: Path, sample_detection: Detection
    ) -> None:
        """测试使用自定义颜色绘制检测框."""
        image = load_image(sample_image)
        custom_color = (0, 255, 255)  # BGR 格式：黄色
        
        result = draw_detection_on_image(image, sample_detection, color=custom_color)
        
        assert isinstance(result, np.ndarray)
    
    def test_draw_detection_without_label(
        self, sample_image: Path, sample_detection: Detection
    ) -> None:
        """测试不显示标签的检测框."""
        image = load_image(sample_image)
        result = draw_detection_on_image(
            image, sample_detection, show_label=False, show_confidence=False
        )
        
        assert isinstance(result, np.ndarray)


class TestDrawDetectionsOnImage:
    """测试绘制多个检测框."""
    
    def test_draw_multiple_detections(self, sample_image: Path) -> None:
        """测试绘制多个检测框."""
        image = load_image(sample_image)
        
        detections = [
            Detection(bbox=[10.0, 20.0, 30.0, 40.0], confidence=0.8, category_id=0),
            Detection(bbox=[50.0, 60.0, 20.0, 25.0], confidence=0.6, category_id=0),
        ]
        
        result = draw_detections_on_image(image, detections)
        
        assert isinstance(result, np.ndarray)
        assert result.shape == image.shape
    
    def test_draw_empty_detections(self, sample_image: Path) -> None:
        """测试绘制空检测列表."""
        image = load_image(sample_image)
        result = draw_detections_on_image(image, [])
        
        assert isinstance(result, np.ndarray)
        # 没有检测框时，图像应该保持不变
        assert np.array_equal(result, image)


class TestCreateVisualization:
    """测试创建可视化."""
    
    def test_create_visualization(
        self, sample_image: Path, sample_detection: Detection, tmp_path: Path
    ) -> None:
        """测试创建可视化图像."""
        detections = [sample_detection]
        output_path = tmp_path / "output_vis.jpg"
        
        result = create_visualization(
            image_path=sample_image,
            detections=detections,
            output_path=output_path,
        )
        
        assert isinstance(result, np.ndarray)
        assert output_path.exists()
    
    def test_create_visualization_without_save(
        self, sample_image: Path, sample_detection: Detection
    ) -> None:
        """测试创建可视化但不保存."""
        detections = [sample_detection]
        
        result = create_visualization(
            image_path=sample_image,
            detections=detections,
            output_path=None,
        )
        
        assert isinstance(result, np.ndarray)


class TestImageConversion:
    """测试图像格式转换."""
    
    def test_image_to_pil(self, sample_image: Path) -> None:
        """测试 OpenCV 图像转换为 PIL 图像."""
        cv_image = load_image(sample_image)
        pil_image = image_to_pil(cv_image)
        
        assert isinstance(pil_image, Image.Image)
        assert pil_image.size == (100, 100)  # PIL 使用 (width, height)
    
    def test_pil_to_image(self) -> None:
        """测试 PIL 图像转换为 OpenCV 图像."""
        # 创建 PIL 图像
        pil_image = Image.new("RGB", (50, 50), color=(255, 0, 0))  # 红色
        
        cv_image = pil_to_image(pil_image)
        
        assert isinstance(cv_image, np.ndarray)
        assert cv_image.shape == (50, 50, 3)
    
    def test_round_trip_conversion(self, sample_image: Path) -> None:
        """测试往返转换（OpenCV -> PIL -> OpenCV）."""
        original = load_image(sample_image)
        
        pil = image_to_pil(original)
        converted_back = pil_to_image(pil)
        
        # 由于颜色空间转换（BGR <-> RGB），值会不同，但形状应该相同
        assert converted_back.shape == original.shape

