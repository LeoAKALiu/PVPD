"""测试数据模型."""

from typing import TYPE_CHECKING

import pytest

from src.inference.models import Detection

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


def test_detection_creation() -> None:
    """测试创建 Detection 对象."""
    detection = Detection(
        bbox=[10.0, 20.0, 100.0, 50.0],
        confidence=0.85,
        category_id=0,
        category_name="pile",
    )
    
    assert detection.bbox == [10.0, 20.0, 100.0, 50.0]
    assert detection.confidence == 0.85
    assert detection.category_id == 0
    assert detection.category_name == "pile"
    assert detection.x_center == 60.0  # 10 + 100/2
    assert detection.y_center == 45.0  # 20 + 50/2


def test_detection_without_category_name() -> None:
    """测试创建不带类别名称的 Detection 对象."""
    detection = Detection(
        bbox=[0.0, 0.0, 50.0, 50.0],
        confidence=0.5,
        category_id=1,
    )
    
    assert detection.category_name is None
    assert detection.x_center == 25.0
    assert detection.y_center == 25.0


def test_detection_to_dict() -> None:
    """测试 Detection 转换为字典."""
    detection = Detection(
        bbox=[10.0, 20.0, 100.0, 50.0],
        confidence=0.85,
        category_id=0,
        category_name="pile",
    )
    
    result = detection.to_dict()
    
    assert isinstance(result, dict)
    assert result["bbox"] == [10.0, 20.0, 100.0, 50.0]
    assert result["confidence"] == 0.85
    assert result["category_id"] == 0
    assert result["category_name"] == "pile"
    assert result["x_center"] == 60.0
    assert result["y_center"] == 45.0


def test_detection_to_sgf_format() -> None:
    """测试 Detection 转换为 SolarGeoFix 格式."""
    detection = Detection(
        bbox=[10.0, 20.0, 100.0, 50.0],
        confidence=0.85,
        category_id=0,
    )
    
    result = detection.to_sgf_format()
    
    assert isinstance(result, dict)
    assert result["x_center"] == 60.0
    assert result["y_center"] == 45.0
    assert result["width"] == 100.0
    assert result["height"] == 50.0
    assert result["confidence"] == 0.85


def test_detection_with_explicit_center() -> None:
    """测试显式指定中心点的 Detection."""
    detection = Detection(
        bbox=[10.0, 20.0, 100.0, 50.0],
        confidence=0.85,
        category_id=0,
        x_center=70.0,
        y_center=55.0,
    )
    
    assert detection.x_center == 70.0
    assert detection.y_center == 55.0



