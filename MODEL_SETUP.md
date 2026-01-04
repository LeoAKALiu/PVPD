# 模型文件配置说明

## 📋 模型文件位置

项目已检测到模型文件在当前目录：`best.pt` (5.4MB)

## 🔧 配置说明

### 当前配置

- **本地模型路径**: `/Users/leo/code/PVPD/best.pt`
- **Docker 容器内路径**: `/app/models/best.pt`

### Docker 容器挂载

为了确保 Docker 容器能访问模型文件，需要在启动容器时挂载模型文件：

```bash
# 方式 1: 使用 docker run（如果手动启动容器）
docker run -v /Users/leo/code/PVPD/best.pt:/app/models/best.pt ...

# 方式 2: 在 docker-compose.yml 中添加卷挂载
volumes:
  - ./best.pt:/app/models/best.pt
  - ./input:/app/input
  - ./output:/app/output
```

### 环境变量配置（可选）

如果需要使用不同的模型路径，可以设置环境变量：

```bash
export PV_PILE_MODEL_WEIGHTS="/app/models/best.pt"
```

## 🚀 启动应用

### 方式 1: 使用启动脚本（推荐）

```bash
./run.sh
```

### 方式 2: 直接使用 Python 模块

```bash
python3 -m streamlit run app.py
```

### 方式 3: 指定端口

```bash
python3 -m streamlit run app.py --server.port 8501
```

## ⚠️ 注意事项

1. **Docker 容器挂载**: 确保 Docker 容器在启动时挂载了模型文件
2. **路径一致性**: 容器内的路径 `/app/models/best.pt` 需要与实际挂载路径一致
3. **文件权限**: 确保模型文件有读取权限

## 🔍 验证配置

运行以下命令验证配置：

```bash
python3 -c "import config; print(f'容器内模型路径: {config.MODEL_WEIGHTS}'); print(f'本地模型路径: {config.LOCAL_MODEL_PATH}')"
```

---

*最后更新: 2025-01-27*

