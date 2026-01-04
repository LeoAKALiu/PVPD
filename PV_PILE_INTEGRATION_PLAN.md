# PV Pile + SolarGeoFix 集成项目规划

## 📋 项目概述

创建一个新的集成项目，将 **PV Pile**（YOLOv11+SAHI 检测）和 **SolarGeoFix**（几何校正）整合到一个统一的 Streamlit 应用中。

## 🎯 功能需求

1. **图像导入**：在 Streamlit 中上传无人机正摄航拍图像
2. **SAHI 推理**：使用 PV Pile 的 Docker 方法进行切片推理
3. **结果可视化**：显示三次图像
   - 原图
   - 推理结果拼图（用红/黄/绿标识置信度）
   - 几何校正后的最终结果
4. **几何校正**：使用 SolarGeoFix 的方法进行后处理

## 🏗️ 架构设计

### 技术栈

- **前端**: Streamlit
- **推理后端**: Docker (PV Pile 容器)
- **几何校正**: SolarGeoFix 模块
- **数据流**: 
  ```
  用户上传图像 
  → Streamlit 接收 
  → 调用 Docker 推理 
  → 解析 JSON 结果 
  → 拼合图像并可视化 
  → 几何校正 
  → 显示最终结果
  ```

### 项目结构（建议）

```
pv_pile_integration/
├── src/
│   ├── inference/
│   │   ├── docker_client.py      # Docker 推理客户端
│   │   └── result_parser.py      # 解析 SAHI JSON 结果
│   ├── visualization/
│   │   ├── image_stitcher.py     # 拼合推理结果图像
│   │   └── confidence_colors.py  # 置信度颜色映射
│   ├── geometry/
│   │   └── corrector.py          # 集成 SolarGeoFix 几何校正
│   └── utils/
│       └── file_handler.py       # 文件处理工具
├── app.py                         # Streamlit 主应用
├── docker-compose.yml             # Docker 配置（可选）
├── requirements.txt
├── README.md
└── tests/
```

## 📝 任务分解

### Phase 1: 项目初始化

- [ ] 创建新项目目录结构
- [ ] 设置依赖管理（requirements.txt 或 pyproject.toml）
- [ ] 配置 Docker 环境（复用 PV Pile 的 Docker 配置）
- [ ] 创建基础 Streamlit 应用框架

### Phase 2: Docker 推理集成

- [ ] 实现 Docker 客户端模块
  - [ ] 检查 Docker 容器状态
  - [ ] 调用 PV Pile 推理接口（通过 docker exec 或 API）
  - [ ] 处理推理结果文件（JSON + 图像）
- [ ] 实现结果解析模块
  - [ ] 解析 COCO 格式 JSON
  - [ ] 提取检测框、置信度、类别信息
  - [ ] 处理坐标转换

### Phase 3: 可视化模块

- [ ] 实现图像拼合模块
  - [ ] 读取推理结果图像
  - [ ] 根据 JSON 结果拼合标注图像
  - [ ] 处理置信度映射（红/黄/绿）
- [ ] 实现置信度颜色映射
  - [ ] 定义置信度阈值（高/中/低）
  - [ ] 颜色映射函数
  - [ ] 绘制带颜色的检测框

### Phase 4: 几何校正集成

- [ ] 集成 SolarGeoFix 几何校正模块
  - [ ] 复制/引用 SolarGeoFix 的几何校正代码
  - [ ] 适配数据格式（从 SAHI JSON 转换为 SGF 格式）
  - [ ] 实现几何校正调用接口
- [ ] 处理校正结果
  - [ ] 可视化校正后的结果
  - [ ] 显示统计信息（修正的检测数等）

### Phase 5: Streamlit UI 开发

- [ ] 设计用户界面布局
  - [ ] 文件上传组件
  - [ ] 参数配置面板（切片大小、置信度阈值等）
  - [ ] 三个图像显示区域（原图、推理结果、校正结果）
  - [ ] 进度指示器
- [ ] 实现交互逻辑
  - [ ] 文件上传处理
  - [ ] 推理触发按钮
  - [ ] 结果显示切换
  - [ ] 参数调整功能

### Phase 6: 测试和优化

- [ ] 单元测试
  - [ ] Docker 客户端测试
  - [ ] 结果解析测试
  - [ ] 可视化模块测试
- [ ] 集成测试
  - [ ] 端到端流程测试
  - [ ] 错误处理测试
- [ ] 性能优化
  - [ ] 图像处理优化
  - [ ] 缓存机制
  - [ ] 异步处理（可选）

## 🔌 接口设计

### Docker 推理接口

```python
def run_docker_inference(
    image_path: str,
    weights_path: str,
    output_dir: str,
    slice_height: int = 640,
    slice_width: int = 640,
    conf_threshold: float = 0.25,
) -> Dict[str, Any]:
    """
    调用 Docker 容器运行推理
    
    Returns:
        {
            'json_path': str,
            'image_path': str,
            'stats': dict
        }
    """
    pass
```

### 结果解析接口

```python
def parse_sahi_results(json_path: str) -> List[Detection]:
    """
    解析 SAHI JSON 结果
    
    Returns:
        List[Detection] 检测结果列表
    """
    pass
```

### 几何校正接口

```python
def apply_geometric_correction(
    detections: List[Detection],
    image_shape: Tuple[int, int]
) -> List[Detection]:
    """
    应用几何校正
    
    Returns:
        校正后的检测结果列表
    """
    pass
```

## 📊 数据流

1. **输入**: 用户上传图像文件（PNG/JPG）
2. **推理阶段**:
   - 图像 → Docker 容器
   - 容器内运行 SAHI 推理
   - 输出: JSON + 标注图像
3. **解析阶段**:
   - 读取 JSON 文件
   - 解析检测结果
   - 提取坐标、置信度、类别
4. **可视化阶段**:
   - 在原图上绘制检测框
   - 根据置信度着色（红/黄/绿）
   - 显示推理结果图像
5. **校正阶段**:
   - 将检测结果输入几何校正模块
   - 执行 RANSAC 回归和网格填充
   - 生成校正后的检测结果
6. **输出**: 显示三张图像（原图、推理结果、校正结果）

## 🔧 技术细节

### Docker 集成方式

**方案 A**: 通过 `docker exec` 调用（推荐）
```bash
docker exec pv_pile_detection python src/inference/sahi_inference.py \
    --weights /app/runs/detect/train4/weights/best.pt \
    --source /app/input/image.jpg \
    --output-dir /app/output \
    --save-img --save-json
```

**方案 B**: 通过 Docker API（Python docker 库）
```python
import docker
client = docker.from_env()
container = client.containers.get('pv_pile_detection')
container.exec_run(...)
```

### 置信度颜色映射

```python
def get_confidence_color(confidence: float) -> str:
    """返回置信度对应的颜色"""
    if confidence >= 0.7:
        return 'green'  # 高置信度
    elif confidence >= 0.4:
        return 'yellow'  # 中置信度
    else:
        return 'red'  # 低置信度
```

### 数据格式转换

**SAHI JSON 格式** (COCO):
```json
{
  "images": [...],
  "annotations": [
    {
      "bbox": [x, y, width, height],
      "score": 0.85,
      "category_id": 0
    }
  ]
}
```

**SolarGeoFix 格式**:
```python
{
  "x_center": float,
  "y_center": float,
  "width": float,
  "height": float,
  "confidence": float
}
```

## 📦 依赖项

```txt
streamlit>=1.28.0
docker>=6.0.0
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
pandas>=2.0.0
matplotlib>=3.7.0
```

## 🚀 部署方案

### 本地开发

1. 确保 PV Pile Docker 容器运行中
2. 安装集成项目依赖
3. 运行 Streamlit 应用

### 生产部署

- 使用 Docker Compose 管理多个服务
- 或使用 Kubernetes 部署
- 考虑使用 Redis 缓存推理结果

## ⚠️ 注意事项

1. **Docker 容器状态**: 需要确保 PV Pile 容器在运行
2. **文件路径**: 注意 Docker 容器内外的路径映射
3. **性能**: 大图像推理可能需要较长时间，考虑进度提示
4. **错误处理**: 妥善处理 Docker 调用失败、文件不存在等情况
5. **数据格式**: 确保 SAHI JSON 和 SolarGeoFix 格式的正确转换

## 🔗 相关项目

- **PV Pile**: https://github.com/LeoAKALiu/pv_pile
- **SolarGeoFix**: https://github.com/LeoAKALiu/SolarGeoFix

---

*创建日期: 2025-01-27*

