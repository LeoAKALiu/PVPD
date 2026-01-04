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
4. **几何校正**: 使用 RANSAC 回归和网格填充算法修正检测结果

## 🚀 快速开始

### 前置要求

1. **Python**: Python 3.10+
2. **Docker**: 已安装并运行 Docker Desktop
3. **PV Pile 容器**: PV Pile 的 Docker 容器已构建并运行
4. **模型文件**: 训练好的 YOLOv11 模型权重文件

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd PVPD
```

#### 2. 创建虚拟环境

```bash
# 使用 uv（推荐）
uv venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 或使用传统方式
python -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置 PV Pile Docker 容器

确保 PV Pile 容器正在运行：

```bash
# 检查容器状态
docker ps | grep pv_pile

# 如果未运行，启动容器（在 PV Pile 项目目录中）
cd /path/to/pv_pile
./docker_start.sh start
```

#### 5. 配置环境变量（可选）

创建 `.env` 文件或设置环境变量：

```bash
export PV_PILE_CONTAINER_NAME="pv_pile_detection"
export PV_PILE_MODEL_WEIGHTS="/app/runs/detect/train4/weights/best.pt"
```

#### 6. 配置模型文件（如果模型文件在当前目录）

如果模型文件 `best.pt` 在当前项目目录下，配置会自动检测并使用它。
确保 Docker 容器在启动时挂载了模型文件（见 [MODEL_SETUP.md](MODEL_SETUP.md)）。

#### 7. 运行应用

**方式 1: 使用启动脚本（推荐）**
```bash
./run.sh
```

**方式 2: 使用 Python 模块**
```bash
python3 -m streamlit run app.py
```

应用将在浏览器中打开（默认: http://localhost:8501）

**注意**: 如果遇到 `streamlit: bad interpreter` 错误，请使用 `python3 -m streamlit` 方式运行。

## 📁 项目结构

```
PVPD/
├── src/
│   ├── inference/          # 推理模块
│   │   ├── docker_client.py      # Docker 推理客户端
│   │   ├── result_parser.py       # SAHI JSON 结果解析
│   │   └── models.py              # 数据模型
│   ├── visualization/      # 可视化模块
│   │   ├── image_stitcher.py      # 图像拼合
│   │   └── confidence_colors.py   # 置信度颜色映射
│   ├── geometry/           # 几何校正模块
│   │   └── corrector.py            # 几何校正（RANSAC + 网格填充）
│   └── utils/              # 工具模块
├── tests/                   # 测试文件
├── app.py                   # Streamlit 主应用
├── config.py                # 配置文件
├── requirements.txt         # Python 依赖
├── AGENTS.md                # AI 代理开发指南
└── README.md                # 本文件
```

## 💻 使用方法

### 基本流程

1. **上传图像**
   - 点击文件上传区域
   - 选择无人机正摄航拍图像（PNG/JPG）
   - 图像将显示在"原始图像"区域

2. **配置参数**（侧边栏）
   - **推理参数**:
     - 切片高度/宽度（默认 640×640）
     - 置信度阈值（默认 0.25）
     - 重叠比例（默认 0.2）
   - **几何校正参数**:
     - 使用 RANSAC 回归（默认开启）
     - 使用网格填充（默认开启）
     - RANSAC 多项式次数（默认 2）
     - RANSAC 残差阈值（默认 10.0）
     - 网格间距（默认 50.0）

3. **运行推理**
   - 点击"🚀 运行推理"按钮
   - 等待 Docker 容器完成推理（显示进度条）
   - 推理结果将自动显示

4. **查看结果**
   - **推理结果**: 显示检测统计和可视化图像
   - **几何校正结果**: 显示校正统计和校正后的可视化图像
   - 可以下载图像和 JSON 结果

## 🎨 界面特性

- **治愈系配色**: 参考 Duolingo/Dailyo 风格的绿色主题
- **响应式设计**: 适配不同屏幕尺寸
- **实时统计**: 显示详细的检测和校正统计信息
- **可视化展示**: 使用颜色编码显示置信度（🟢高/🟡中/🔴低）
- **结果导出**: 支持下载图像和 JSON 格式结果

## 🔧 配置说明

### 配置文件

主要配置在 `config.py` 中，支持环境变量覆盖：

```python
# Docker 配置
CONTAINER_NAME = "pv_pile_detection"
MODEL_WEIGHTS = "/app/runs/detect/train4/weights/best.pt"

# 推理参数
DEFAULT_SLICE_HEIGHT = 640
DEFAULT_SLICE_WIDTH = 640
DEFAULT_CONF_THRESHOLD = 0.25

# 置信度颜色阈值
HIGH_CONF_THRESHOLD = 0.7    # 绿色
MEDIUM_CONF_THRESHOLD = 0.4   # 黄色
LOW_CONF_THRESHOLD = 0.0     # 红色
```

### Docker 容器配置

确保 Docker 容器配置包含以下卷挂载：

```yaml
volumes:
  - ./input:/app/input      # 输入图像
  - ./output:/app/output    # 输出结果
  - ./runs:/app/runs        # 模型权重
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_docker_client.py

# 运行带覆盖率的测试
pytest --cov=src tests/

# 运行集成测试
pytest tests/test_integration.py
```

### 代码质量检查

```bash
# 使用 Ruff 进行代码检查
ruff check src/

# 格式化代码
ruff format src/
```

## 📊 性能参考

- **推理时间**: 取决于图像大小和切片参数
  - 单张 4000×3000 图像: ~30-60 秒（CPU）
  - 单张 8000×6000 图像: ~2-5 分钟（CPU）
- **几何校正时间**: ~1-5 秒
- **内存占用**: ~2-4 GB

## 🐛 故障排除

### Docker 容器未运行

```bash
# 检查容器状态
docker ps | grep pv_pile

# 启动容器
cd /path/to/pv_pile && ./docker_start.sh start
```

### 模型文件未找到

```bash
# 检查模型文件是否存在
docker exec pv_pile_detection ls -lh /app/runs/detect/train4/weights/best.pt
```

### 推理失败

- 检查 Docker 容器日志: `docker logs pv_pile_detection`
- 检查输入图像格式（支持 PNG/JPG）
- 检查磁盘空间是否充足

## 📦 依赖项

主要依赖：

- `streamlit>=1.28.0` - Web 应用框架
- `docker>=6.0.0` - Docker API
- `opencv-python>=4.8.0` - 图像处理
- `numpy>=1.24.0` - 数值计算
- `scikit-learn>=1.3.0` - RANSAC 回归
- `scipy>=1.11.0` - 距离计算
- `pytest>=7.4.0` - 测试框架

完整依赖列表请查看 `requirements.txt`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目基于 PV Pile 和 SolarGeoFix 的许可证。

## 🔗 相关项目

- **PV Pile**: https://github.com/LeoAKALiu/pv_pile - YOLOv11+SAHI 检测系统
- **SolarGeoFix**: https://github.com/LeoAKALiu/SolarGeoFix - 几何校正系统

## 📝 开发文档

- [AGENTS.md](AGENTS.md) - AI 代理开发指南
- [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) - 开发计划
- [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) - Phase 1 完成报告
- [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) - Phase 2 完成报告
- [PHASE3_COMPLETE.md](PHASE3_COMPLETE.md) - Phase 3 完成报告
- [PHASE4_COMPLETE.md](PHASE4_COMPLETE.md) - Phase 4 完成报告

---

*最后更新: 2025-01-27*

