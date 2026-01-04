"""测试结果解析模块."""

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from src.inference.models import Detection
from src.inference.result_parser import get_detection_stats, parse_sahi_results

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


@pytest.fixture
def sample_json_file(tmp_path: Path) -> Path:
    """创建示例 JSON 文件."""
    json_path = tmp_path / "test_results.json"
    
    data = {
        "images": [
            {
                "id": 0,
                "file_name": "test_image.jpg",
                "width": 1000,
                "height": 800,
            }
        ],
        "annotations": [
            {
                "id": 0,
                "image_id": 0,
                "bbox": [10.0, 20.0, 100.0, 50.0],
                "score": 0.85,
                "category_id": 0,
                "category_name": "pile",
            },
            {
                "id": 1,
                "image_id": 0,
                "bbox": [200.0, 300.0, 80.0, 60.0],
                "score": 0.65,
                "category_id": 0,
                "category_name": "pile",
            },
            {
                "id": 2,
                "image_id": 0,
                "bbox": [500.0, 100.0, 120.0, 90.0],
                "score": 0.35,
                "category_id": 0,
            },
        ],
    }
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    
    return json_path


class TestParseSahiResults:
    """测试解析 SAHI 结果."""
    
    def test_successful_parsing(self, sample_json_file: Path) -> None:
        """测试成功解析 JSON."""
        detections = parse_sahi_results(sample_json_file)
        
        assert len(detections) == 3
        assert all(isinstance(d, Detection) for d in detections)
        
        # 检查第一个检测结果
        assert detections[0].bbox == [10.0, 20.0, 100.0, 50.0]
        assert detections[0].confidence == 0.85
        assert detections[0].category_id == 0
        assert detections[0].category_name == "pile"
    
    def test_file_not_found(self, tmp_path: Path) -> None:
        """测试文件不存在的情况."""
        json_path = tmp_path / "nonexistent.json"
        
        with pytest.raises(FileNotFoundError, match="JSON 文件不存在"):
            parse_sahi_results(json_path)
    
    def test_invalid_json(self, tmp_path: Path) -> None:
        """测试无效的 JSON 格式."""
        json_path = tmp_path / "invalid.json"
        json_path.write_text("这不是有效的 JSON")
        
        with pytest.raises(ValueError, match="无效的 JSON 格式"):
            parse_sahi_results(json_path)
    
    def test_missing_annotations(self, tmp_path: Path) -> None:
        """测试缺少 annotations 字段的情况."""
        json_path = tmp_path / "missing_annotations.json"
        json_path.write_text('{"images": []}')
        
        with pytest.raises(KeyError, match="缺少 'annotations' 字段"):
            parse_sahi_results(json_path)
    
    def test_invalid_annotations_type(self, tmp_path: Path) -> None:
        """测试 annotations 不是列表的情况."""
        json_path = tmp_path / "invalid_annotations.json"
        json_path.write_text('{"annotations": "not a list"}')
        
        with pytest.raises(ValueError, match="'annotations' 必须是列表"):
            parse_sahi_results(json_path)
    
    def test_missing_bbox_field(self, tmp_path: Path) -> None:
        """测试缺少 bbox 字段的情况."""
        json_path = tmp_path / "missing_bbox.json"
        data = {
            "annotations": [
                {
                    "score": 0.85,
                    "category_id": 0,
                }
            ]
        }
        json_path.write_text(json.dumps(data))
        
        detections = parse_sahi_results(json_path)
        
        # 应该跳过无效的注释
        assert len(detections) == 0
    
    def test_invalid_bbox_format(self, tmp_path: Path) -> None:
        """测试无效的 bbox 格式."""
        json_path = tmp_path / "invalid_bbox.json"
        data = {
            "annotations": [
                {
                    "bbox": [10.0, 20.0],  # 长度不足
                    "score": 0.85,
                    "category_id": 0,
                }
            ]
        }
        json_path.write_text(json.dumps(data))
        
        detections = parse_sahi_results(json_path)
        
        # 应该跳过无效的注释
        assert len(detections) == 0
    
    def test_invalid_confidence_range(self, tmp_path: Path) -> None:
        """测试置信度超出范围的情况."""
        json_path = tmp_path / "invalid_confidence.json"
        data = {
            "annotations": [
                {
                    "bbox": [10.0, 20.0, 100.0, 50.0],
                    "score": 1.5,  # 超出范围
                    "category_id": 0,
                }
            ]
        }
        json_path.write_text(json.dumps(data))
        
        detections = parse_sahi_results(json_path)
        
        # 应该跳过无效的注释
        assert len(detections) == 0


class TestGetDetectionStats:
    """测试获取检测统计信息."""
    
    def test_empty_detections(self) -> None:
        """测试空检测列表."""
        stats = get_detection_stats([])
        
        assert stats["total"] == 0
        assert stats["high_confidence"] == 0
        assert stats["medium_confidence"] == 0
        assert stats["low_confidence"] == 0
        assert stats["avg_confidence"] == 0.0
        assert stats["categories"] == {}
    
    def test_stats_calculation(self) -> None:
        """测试统计信息计算."""
        detections = [
            Detection(bbox=[10, 20, 100, 50], confidence=0.85, category_id=0),  # 高置信度
            Detection(bbox=[200, 300, 80, 60], confidence=0.65, category_id=0),  # 中置信度
            Detection(bbox=[500, 100, 120, 90], confidence=0.35, category_id=0),  # 低置信度
            Detection(bbox=[600, 200, 90, 70], confidence=0.75, category_id=1),  # 高置信度，不同类别
        ]
        
        stats = get_detection_stats(detections)
        
        assert stats["total"] == 4
        assert stats["high_confidence"] == 2  # 0.85, 0.75
        assert stats["medium_confidence"] == 1  # 0.65
        assert stats["low_confidence"] == 1  # 0.35
        assert stats["avg_confidence"] == pytest.approx(0.65, abs=0.01)
        assert stats["categories"][0] == 3
        assert stats["categories"][1] == 1

