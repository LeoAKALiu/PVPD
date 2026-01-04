# PV Pile Integration - 光伏板桩基检测集成系统

## 📋 项目简介

本项目整合了 **PV Pile**（YOLOv11+SAHI 检测）和 **SolarGeoFix**（几何校正）两个系统，提供一个统一的 Streamlit Web 应用，实现从图像上传到最终校正结果的完整工作流。

## ✨ 核心功能

1. **图像上传**: 支持上传无人机正摄航拍图像（PNG/JPG）
2. **SAHI 推理**: 使用 Docker 容器化的 PV Pile 系统进行切片推理
3. **可视化展示**: 分三步显示处理结果
   - 📷 **原图**: 用户上传的原始图像
   - 🔍 **推理结果**: SAHI 检测结果，使用红/黄/绿颜色标识置信度
   - ✅ **几何校正**: 经过几何校正后的最终结果
4. **几何校正**: 使用 SolarGeoFix 的 RANSAC 回归和网格填充算法修正检测结果

## 🏗️ 系统架构

```
┌─────────────┐
│  Streamlit  │ 用户界面
│     UI      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Docker     │ PV Pile 推理容器
│  Container  │ (SAHI Inference)
└──────┬──────┘
       │ JSON + Images
       ▼
┌─────────────┐
│   Parser    │ 结果解析
│   Module    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│Visualization│ 图像拼合与可视化
│   Module    │ (置信度颜色映射)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Geometric  │ 几何校正
│  Corrector  │ (SolarGeoFix)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Final     │ 最终结果展示
│   Result    │
└─────────────┘
```

## 🚀 快速开始

### 前置要求

1. **Docker**: 已安装并运行 Docker Desktop
2. **PV Pile 容器**: PV Pile 的 Docker 容器已构建并运行
3. **Python**: Python 3.10+
4. **模型文件**: 训练好的 YOLOv11 模型权重文件

### 安装步骤

#### 1. 创建项目

```bash
# 创建项目目录
mkdir pv_pile_integration
cd pv_pile_integration

# 初始化 Git（可选）
git init
```

#### 2. 设置 Python 环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 配置 PV Pile Docker 容器

确保 PV Pile 容器正在运行：

```bash
# 进入 PV Pile 项目目录
cd /path/to/pv_pile

# 启动容器
./docker_start.sh start

# 或使用 docker-compose
docker-compose up -d
```

#### 4. 配置模型路径

在项目配置文件中设置模型路径（容器内的路径）：

```python
# config.py
MODEL_WEIGHTS = "/app/runs/detect/train4/weights/best.pt"
CONTAINER_NAME = "pv_pile_detection"
```

#### 5. 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中打开（默认: http://localhost:8501）

## 📁 项目结构

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
├── README.md                      # 本文件
├── .gitignore
└── tests/                         # 测试文件
    ├── test_docker_client.py
    ├── test_parser.py
    └── test_visualization.py
```

## 🔧 配置说明

### Docker 配置

确保 `docker-compose.yml` 或 Docker 容器配置中包含以下卷挂载：

```yaml
volumes:
  - ./input:/app/input      # 输入图像
  - ./output:/app/output    # 输出结果
  - ./runs:/app/runs        # 模型权重
```

### 应用配置

在 `config.py` 中配置：

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

## 💻 使用方法

### 基本流程

1. **上传图像**
   - 点击 "Upload Image" 按钮
   - 选择无人机正摄航拍图像（PNG/JPG）
   - 图像将显示在 "原始图像" 区域

2. **配置参数**（可选）
   - 调整切片大小（默认 640×640）
   - 设置置信度阈值（默认 0.25）
   - 配置重叠比例（默认 0.2）

3. **运行推理**
   - 点击 "Run Inference" 按钮
   - 等待 Docker 容器完成推理（显示进度条）
   - 推理结果将显示在 "推理结果" 区域
   - 检测框颜色：
     - 🟢 **绿色**: 高置信度（≥0.7）
     - 🟡 **黄色**: 中置信度（0.4-0.7）
     - 🔴 **红色**: 低置信度（<0.4）

4. **几何校正**
   - 推理完成后，自动进行几何校正
   - 校正结果显示在 "几何校正结果" 区域
   - 显示统计信息：
     - 原始检测数
     - 校正后检测数
     - 新增/删除的检测数

5. **查看结果**
   - 可以在三个视图间切换
   - 下载最终结果图像
   - 导出 JSON 结果

## 🎨 界面预览

```
┌─────────────────────────────────────────┐
│  PV Pile Integration System             │
├─────────────────────────────────────────┤
│                                         │
│  [Upload Image]  [Run Inference]        │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │  原图    │  │ 推理结果 │  │ 校正结果││
│  │          │  │          │  │        ││
│  │ [Image]  │  │ [Image]  │  │[Image] ││
│  │          │  │          │  │        ││
│  └──────────┘  └──────────┘  └────────┘│
│                                         │
│  统计信息:                               │
│  - 原始检测: 156                         │
│  - 校正后: 162                           │
│  - 新增: +8                              │
│                                         │
└─────────────────────────────────────────┘
```

## 🔌 API 接口

### Docker 推理客户端

```python
from src.inference.docker_client import run_docker_inference

result = run_docker_inference(
    image_path="input/image.jpg",
    weights_path="/app/runs/detect/train4/weights/best.pt",
    output_dir="output",
    slice_height=640,
    slice_width=640,
    conf_threshold=0.25
)
```

### 结果解析

```python
from src.inference.result_parser import parse_sahi_results

detections = parse_sahi_results("output/image.json")
```

### 几何校正

```python
from src.geometry.corrector import apply_geometric_correction

corrected = apply_geometric_correction(
    detections=detections,
    image_shape=(height, width)
)
```

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_docker_client.py

# 带覆盖率
pytest --cov=src tests/
```

## 📦 依赖项

主要依赖：

```txt
streamlit>=1.28.0
docker>=6.0.0
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
scikit-learn>=1.3.0  # 用于 RANSAC（几何校正）
```

完整依赖列表请查看 `requirements.txt`

## 🐛 故障排除

### Docker 容器未运行

```bash
# 检查容器状态
docker ps | grep pv_pile

# 启动容器
cd /path/to/pv_pile
./docker_start.sh start
```

### 模型文件未找到

```bash
# 检查模型文件是否存在
docker exec pv_pile_detection ls -lh /app/runs/detect/train4/weights/best.pt

# 如果不存在，需要复制模型文件到容器中
```

### 推理失败

- 检查 Docker 容器日志: `docker logs pv_pile_detection`
- 检查输入图像格式（支持 PNG/JPG）
- 检查磁盘空间是否充足

## 📊 性能参考

- **推理时间**: 取决于图像大小和切片参数
  - 单张 4000×3000 图像: ~30-60 秒（CPU）
  - 单张 8000×6000 图像: ~2-5 分钟（CPU）
- **几何校正时间**: ~1-5 秒
- **内存占用**: ~2-4 GB

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目基于 PV Pile 和 SolarGeoFix 的许可证。

## 🔗 相关项目

- **PV Pile**: [GitHub](https://github.com/LeoAKALiu/pv_pile) - YOLOv11+SAHI 检测系统
- **SolarGeoFix**: [GitHub](https://github.com/LeoAKALiu/SolarGeoFix) - 几何校正系统

## 📝 开发计划

- [x] 项目规划
- [ ] Phase 1: 项目初始化
- [ ] Phase 2: Docker 推理集成
- [ ] Phase 3: 可视化模块
- [ ] Phase 4: 几何校正集成
- [ ] Phase 5: Streamlit UI 开发
- [ ] Phase 6: 测试和优化

详细开发计划请参考 [INTEGRATION_PLAN.md](INTEGRATION_PLAN.md)

---

*最后更新: 2025-01-27*

