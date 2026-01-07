"""测试 Docker 客户端."""

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pytest
from docker.errors import ContainerError, DockerException, NotFound

from src.inference.docker_client import (
    check_container_status,
    get_container_logs,
    run_docker_inference,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class TestCheckContainerStatus:
    """测试容器状态检查."""
    
    def test_container_running(self, mocker: "MockerFixture") -> None:
        """测试容器正在运行的情况."""
        mock_container = Mock()
        mock_container.status = "running"
        
        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        
        mocker.patch("src.inference.docker_client.docker.from_env", return_value=mock_client)
        
        result = check_container_status("test_container")
        
        assert result is True
        mock_client.containers.get.assert_called_once_with("test_container")
    
    def test_container_not_found(self, mocker: "MockerFixture") -> None:
        """测试容器未找到的情况."""
        mock_client = Mock()
        mock_client.containers.get.side_effect = NotFound("Container not found")
        
        mocker.patch("src.inference.docker_client.docker.from_env", return_value=mock_client)
        
        result = check_container_status("test_container")
        
        assert result is False
    
    def test_docker_exception(self, mocker: "MockerFixture") -> None:
        """测试 Docker 异常的情况."""
        mock_client = Mock()
        mock_client.containers.get.side_effect = DockerException("Docker error")
        
        mocker.patch("src.inference.docker_client.docker.from_env", return_value=mock_client)
        
        result = check_container_status("test_container")
        
        assert result is False


class TestRunDockerInference:
    """测试 Docker 推理功能."""
    
    @pytest.fixture
    def mock_image_path(self, tmp_path: Path) -> Path:
        """创建模拟图像文件."""
        image_path = tmp_path / "test_image.jpg"
        image_path.write_bytes(b"fake image data")
        return image_path
    
    @pytest.fixture
    def mock_output_dir(self, tmp_path: Path) -> Path:
        """创建模拟输出目录."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return output_dir
    
    def test_file_not_found(self, tmp_path: Path) -> None:
        """测试输入文件不存在的情况."""
        image_path = tmp_path / "nonexistent.jpg"
        
        with pytest.raises(FileNotFoundError, match="输入图像不存在"):
            run_docker_inference(
                image_path=image_path,
                output_dir=tmp_path / "output",
            )
    
    def test_invalid_image_format(self, tmp_path: Path) -> None:
        """测试无效的图像格式."""
        image_path = tmp_path / "test.txt"
        image_path.write_text("not an image")
        
        with pytest.raises(ValueError, match="不支持的图像格式"):
            run_docker_inference(
                image_path=image_path,
                output_dir=tmp_path / "output",
            )
    
    def test_container_not_running(
        self, mock_image_path: Path, mock_output_dir: Path, mocker: "MockerFixture"
    ) -> None:
        """测试容器未运行的情况."""
        mocker.patch(
            "src.inference.docker_client.check_container_status",
            return_value=False,
        )
        
        with pytest.raises(RuntimeError, match="容器.*未运行"):
            run_docker_inference(
                image_path=mock_image_path,
                output_dir=mock_output_dir,
            )
    
    @patch("src.inference.docker_client.check_container_status", return_value=True)
    @patch("src.inference.docker_client.docker.from_env")
    @patch("src.inference.docker_client.time.sleep")  # 避免实际等待
    def test_successful_inference(
        self,
        mock_sleep: Mock,
        mock_docker: Mock,
        mock_check: Mock,
        mock_image_path: Path,
        mock_output_dir: Path,
        tmp_path: Path,
    ) -> None:
        """测试成功的推理."""
        # 创建模拟的 JSON 和图像输出文件
        json_path = mock_output_dir / "test_image.json"
        json_path.write_text('{"annotations": []}')
        
        image_path = mock_output_dir / "test_image_prediction.jpg"
        image_path.write_bytes(b"fake prediction image")
        
        # 模拟 Docker 容器
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 0
        mock_exec_result.output = b""
        
        mock_container = Mock()
        mock_container.exec_run.return_value = mock_exec_result
        
        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client
        
        result = run_docker_inference(
            image_path=mock_image_path,
            output_dir=mock_output_dir,
        )
        
        assert "json_path" in result
        assert "image_path" in result
        assert "stats" in result
        assert Path(result["json_path"]).exists()
        assert Path(result["image_path"]).exists()
    
    @patch("src.inference.docker_client.check_container_status", return_value=True)
    @patch("src.inference.docker_client.docker.from_env")
    def test_inference_failure(
        self,
        mock_docker: Mock,
        mock_check: Mock,
        mock_image_path: Path,
        mock_output_dir: Path,
    ) -> None:
        """测试推理失败的情况."""
        # 模拟 Docker 容器执行失败
        mock_exec_result = Mock()
        mock_exec_result.exit_code = 1
        mock_exec_result.output = b"Error: Model not found"
        
        mock_container = Mock()
        mock_container.exec_run.return_value = mock_exec_result
        
        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        mock_docker.return_value = mock_client
        
        with pytest.raises(RuntimeError, match="Docker 推理失败"):
            run_docker_inference(
                image_path=mock_image_path,
                output_dir=mock_output_dir,
            )


class TestGetContainerLogs:
    """测试获取容器日志."""
    
    def test_successful_log_retrieval(self, mocker: "MockerFixture") -> None:
        """测试成功获取日志."""
        mock_container = Mock()
        mock_container.logs.return_value = b"Log line 1\nLog line 2\n"
        
        mock_client = Mock()
        mock_client.containers.get.return_value = mock_container
        
        mocker.patch("src.inference.docker_client.docker.from_env", return_value=mock_client)
        
        logs = get_container_logs("test_container", tail=10)
        
        assert "Log line 1" in logs
        assert "Log line 2" in logs
        mock_container.logs.assert_called_once_with(tail=10)
    
    def test_log_retrieval_failure(self, mocker: "MockerFixture") -> None:
        """测试获取日志失败的情况."""
        mock_client = Mock()
        mock_client.containers.get.side_effect = Exception("Connection error")
        
        mocker.patch("src.inference.docker_client.docker.from_env", return_value=mock_client)
        
        logs = get_container_logs("test_container")
        
        assert "无法获取日志" in logs



