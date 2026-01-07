"""测试置信度颜色映射."""

from typing import TYPE_CHECKING

import pytest

from src.visualization.confidence_colors import (
    get_confidence_color,
    get_confidence_color_bgr,
    get_confidence_color_rgb,
    get_confidence_emoji,
    get_confidence_label,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class TestGetConfidenceColor:
    """测试 get_confidence_color 函数."""
    
    def test_high_confidence(self) -> None:
        """测试高置信度."""
        assert get_confidence_color(0.8) == "green"
        assert get_confidence_color(0.7) == "green"
        assert get_confidence_color(1.0) == "green"
    
    def test_medium_confidence(self) -> None:
        """测试中置信度."""
        assert get_confidence_color(0.5) == "yellow"
        assert get_confidence_color(0.4) == "yellow"
        assert get_confidence_color(0.69) == "yellow"
    
    def test_low_confidence(self) -> None:
        """测试低置信度."""
        assert get_confidence_color(0.3) == "red"
        assert get_confidence_color(0.0) == "red"
        assert get_confidence_color(0.39) == "red"


class TestGetConfidenceColorRgb:
    """测试 get_confidence_color_rgb 函数."""
    
    def test_high_confidence(self) -> None:
        """测试高置信度 RGB."""
        assert get_confidence_color_rgb(0.8) == (0, 255, 0)  # 绿色
    
    def test_medium_confidence(self) -> None:
        """测试中置信度 RGB."""
        assert get_confidence_color_rgb(0.5) == (255, 255, 0)  # 黄色
    
    def test_low_confidence(self) -> None:
        """测试低置信度 RGB."""
        assert get_confidence_color_rgb(0.3) == (255, 0, 0)  # 红色


class TestGetConfidenceColorBgr:
    """测试 get_confidence_color_bgr 函数."""
    
    def test_high_confidence(self) -> None:
        """测试高置信度 BGR."""
        assert get_confidence_color_bgr(0.8) == (0, 255, 0)  # BGR 绿色
    
    def test_medium_confidence(self) -> None:
        """测试中置信度 BGR."""
        assert get_confidence_color_bgr(0.5) == (0, 255, 255)  # BGR 黄色
    
    def test_low_confidence(self) -> None:
        """测试低置信度 BGR."""
        assert get_confidence_color_bgr(0.3) == (0, 0, 255)  # BGR 红色


class TestGetConfidenceLabel:
    """测试 get_confidence_label 函数."""
    
    def test_high_confidence(self) -> None:
        """测试高置信度标签."""
        assert get_confidence_label(0.8) == "高置信度"
    
    def test_medium_confidence(self) -> None:
        """测试中置信度标签."""
        assert get_confidence_label(0.5) == "中置信度"
    
    def test_low_confidence(self) -> None:
        """测试低置信度标签."""
        assert get_confidence_label(0.3) == "低置信度"


class TestGetConfidenceEmoji:
    """测试 get_confidence_emoji 函数."""
    
    def test_high_confidence(self) -> None:
        """测试高置信度表情."""
        assert get_confidence_emoji(0.8) == "🟢"
    
    def test_medium_confidence(self) -> None:
        """测试中置信度表情."""
        assert get_confidence_emoji(0.5) == "🟡"
    
    def test_low_confidence(self) -> None:
        """测试低置信度表情."""
        assert get_confidence_emoji(0.3) == "🔴"



