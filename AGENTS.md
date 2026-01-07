# AGENTS.md

AGENTS.md 是用于指导 AI 编码代理的简单、开放格式文件。

## 项目概述

本项目是一个**光伏板桩基检测集成系统**，整合了 PV Pile（YOLOv11+SAHI 检测）和 SolarGeoFix（几何校正）两个系统，提供一个统一的 Streamlit Web 应用。

### 核心功能
1. 图像上传：支持上传无人机正摄航拍图像（PNG/JPG）
2. SAHI 推理：使用 Docker 容器化的 PV Pile 系统进行切片推理
3. 可视化展示：分三步显示处理结果（原图、推理结果、几何校正结果）
4. 几何校正：使用 SolarGeoFix 的 RANSAC 回归和网格填充算法修正检测结果

## 开发环境设置

### 前置要求
- **Python**: Python 3.10+
- **Docker**: 已安装并运行 Docker Desktop
- **PV Pile 容器**: PV Pile 的 Docker 容器已构建并运行
- **模型文件**: 训练好的 YOLOv11 模型权重文件

### 环境初始化

```bash
# 创建虚拟环境（推荐使用 uv）
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
uv pip install -r requirements.txt

# 或使用传统方式
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Docker 容器管理

```bash
# 检查 PV Pile 容器状态
docker ps | grep pv_pile

# 启动容器（在 PV Pile 项目目录中）
cd /path/to/pv_pile
./docker_start.sh start

# 或使用 docker-compose
docker-compose up -d
```

## 项目结构

```
pv_pile_integration/
├── src/
│   ├── __init__.py
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── docker_client.py      # Docker 推理客户端
│   │   └── result_parser.py      # SAHI JSON 结果解析
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── image_stitcher.py     # 图像拼合
│   │   └── confidence_colors.py  # 置信度颜色映射
│   ├── geometry/
│   │   ├── __init__.py
│   │   └── corrector.py          # 几何校正（集成 SolarGeoFix）
│   └── utils/
│       ├── __init__.py
│       └── file_handler.py       # 文件处理工具
├── app.py                         # Streamlit 主应用
├── config.py                      # 配置文件
├── requirements.txt               # Python 依赖
├── tests/                         # 测试文件
│   ├── __init__.py
│   ├── test_docker_client.py
│   ├── test_parser.py
│   └── test_visualization.py
├── .gitignore
└── README.md
```

## 编码规范

### Python 代码规范

- **类型注解**: 所有函数和类必须包含完整的类型注解，包括返回类型（包括 `None`）
- **文档字符串**: 遵循 PEP 257 规范，所有函数和类必须有描述性文档字符串
- **代码风格**: 使用 Ruff 进行代码格式化和检查
- **注释**: 保留文件中的所有现有注释

### 测试规范

- **测试框架**: 仅使用 pytest 或 pytest 插件（不使用 unittest）
- **类型注解**: 所有测试必须包含类型注解
- **文档字符串**: 所有测试必须包含文档字符串
- **测试位置**: 所有测试放在 `./tests` 目录下
- **导入规范**: 测试文件中应导入以下类型（如果使用）：
  ```python
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from _pytest.capture import CaptureFixture
      from _pytest.fixtures import FixtureRequest
      from _pytest.logging import LogCaptureFixture
      from _pytest.monkeypatch import MonkeyPatch
      from pytest_mock.plugin import MockerFixture
  ```

### 包结构

- 如果创建 `./tests` 或 `./src/<package_name>` 下的包，确保添加 `__init__.py` 文件（如果不存在）

## 开发工作流

### 运行应用

```bash
# 确保 Docker 容器运行中
docker ps | grep pv_pile

# 运行 Streamlit 应用
streamlit run app.py
```

应用将在浏览器中打开（默认: http://localhost:8501）

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_docker_client.py

# 运行带覆盖率的测试
pytest --cov=src tests/

# 运行特定测试函数
pytest tests/test_docker_client.py::test_function_name
```

### 代码检查

```bash
# 使用 Ruff 进行代码格式化和检查
ruff check src/
ruff format src/

# 或使用 pre-commit（如果配置了）
pre-commit run --all-files
```

## 配置管理

### 配置文件位置
- 主要配置在 `config.py` 中
- 使用环境变量管理敏感信息（如 Docker 配置、模型路径）

### 关键配置项

```python
# Docker 配置
CONTAINER_NAME = "pv_pile_detection"
DOCKER_IMAGE = "pv_pile:latest"

# 模型配置
MODEL_WEIGHTS = "/app/runs/detect/train4/weights/best.pt"

# 推理参数
DEFAULT_SLICE_HEIGHT = 640
DEFAULT_SLICE_WIDTH = 640
DEFAULT_CONF_THRESHOLD = 0.25

# 置信度颜色阈值
HIGH_CONF_THRESHOLD = 0.7    # 绿色
MEDIUM_CONF_THRESHOLD = 0.4   # 黄色
LOW_CONF_THRESHOLD = 0.0      # 红色
```

## 模块说明

### Docker 推理客户端 (`src/inference/docker_client.py`)
- 检查 Docker 容器状态
- 调用 PV Pile 推理接口（通过 `docker exec` 或 Docker API）
- 处理推理结果文件（JSON + 图像）

### 结果解析 (`src/inference/result_parser.py`)
- 解析 COCO 格式 JSON
- 提取检测框、置信度、类别信息
- 处理坐标转换

### 可视化模块 (`src/visualization/`)
- **image_stitcher.py**: 读取推理结果图像并拼合标注图像
- **confidence_colors.py**: 根据置信度映射颜色（红/黄/绿）

### 几何校正 (`src/geometry/corrector.py`)
- 集成 SolarGeoFix 几何校正模块
- 适配数据格式（从 SAHI JSON 转换为 SGF 格式）
- 实现几何校正调用接口

## 数据流

1. **输入**: 用户上传图像文件（PNG/JPG）
2. **推理阶段**: 图像 → Docker 容器 → SAHI 推理 → 输出 JSON + 标注图像
3. **解析阶段**: 读取 JSON 文件 → 解析检测结果 → 提取坐标、置信度、类别
4. **可视化阶段**: 在原图上绘制检测框 → 根据置信度着色 → 显示推理结果图像
5. **校正阶段**: 检测结果输入几何校正模块 → 执行 RANSAC 回归和网格填充 → 生成校正后的检测结果
6. **输出**: 显示三张图像（原图、推理结果、校正结果）

## 错误处理

### 常见问题

1. **Docker 容器未运行**
   ```bash
   docker ps | grep pv_pile
   # 如果未运行，启动容器
   cd /path/to/pv_pile && ./docker_start.sh start
   ```

2. **模型文件未找到**
   ```bash
   docker exec pv_pile_detection ls -lh /app/runs/detect/train4/weights/best.pt
   ```

3. **推理失败**
   - 检查 Docker 容器日志: `docker logs pv_pile_detection`
   - 检查输入图像格式（支持 PNG/JPG）
   - 检查磁盘空间是否充足

### 错误处理原则

- 所有 Docker 调用必须包含错误处理
- 文件操作必须检查文件是否存在
- 提供清晰的错误消息和建议的解决方案
- 使用日志记录错误上下文

## 性能考虑

- **推理时间**: 取决于图像大小和切片参数
  - 单张 4000×3000 图像: ~30-60 秒（CPU）
  - 单张 8000×6000 图像: ~2-5 分钟（CPU）
- **几何校正时间**: ~1-5 秒
- **内存占用**: ~2-4 GB

## 提交规范

### 提交前检查清单

- [ ] 运行所有测试: `pytest tests/`
- [ ] 运行代码检查: `ruff check src/`
- [ ] 确保所有函数和类都有类型注解和文档字符串
- [ ] 更新相关文档（如需要）

### 提交信息格式

```
[模块] 简短描述

详细说明（可选）
```

示例：
```
[inference] 添加 Docker 客户端错误处理

- 添加容器状态检查
- 改进错误消息
- 添加日志记录
```

## 相关项目

- **PV Pile**: https://github.com/LeoAKALiu/pv_pile - YOLOv11+SAHI 检测系统
- **SolarGeoFix**: https://github.com/LeoAKALiu/SolarGeoFix - 几何校正系统

## 开发原则

1. **简洁性**: 保持代码简洁，易于理解和维护
2. **健壮性**: 处理边缘情况，提供清晰的错误消息
3. **文档**: 保持文档更新，包括 README 和代码注释
4. **测试**: 为新功能添加测试，确保代码质量

---

*最后更新: 2025-01-27*



