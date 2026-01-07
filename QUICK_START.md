# 快速启动指南

## ✅ 已解决的问题

### 1. Streamlit 启动问题

**问题**: `streamlit: bad interpreter` 错误

**解决方案**: 使用 `python3 -m streamlit` 方式运行，避免路径问题

### 2. 模型文件配置

**状态**: ✅ 已检测到模型文件 `best.pt` (5.4MB) 在当前目录

**配置**:
- 本地路径: `/Users/leo/code/PVPD/best.pt`
- Docker 容器内路径: `/app/models/best.pt`

## 🚀 启动应用

### 方式 1: 使用启动脚本（最简单）

```bash
./run.sh
```

### 方式 2: 使用 Python 模块

```bash
python3 -m streamlit run app.py
```

### 方式 3: 指定端口

```bash
python3 -m streamlit run app.py --server.port 8501
```

应用将在浏览器中自动打开：http://localhost:8501

## 📋 使用前检查

- [x] 依赖已安装
- [x] 所有测试通过 (72/72)
- [x] Docker 容器 `pv_pile_detection` 运行中
- [x] 模型文件 `best.pt` 在当前目录
- [ ] **重要**: 确保 Docker 容器挂载了模型文件

## ⚠️ Docker 容器配置

为了确保 Docker 容器能访问模型文件，需要在启动容器时挂载：

```bash
# 检查容器是否已挂载模型文件
docker inspect pv_pile_detection | grep -A 10 Mounts

# 如果没有挂载，需要重新启动容器并添加卷挂载
# 或者在 docker-compose.yml 中添加：
volumes:
  - ./best.pt:/app/models/best.pt
  - ./input:/app/input
  - ./output:/app/output
```

## 🎯 使用流程

1. **启动应用**: 运行 `./run.sh` 或 `python3 -m streamlit run app.py`
2. **上传图像**: 在浏览器中上传无人机正摄航拍图像
3. **配置参数**: 在侧边栏调整推理和几何校正参数
4. **运行推理**: 点击"🚀 运行推理"按钮
5. **查看结果**: 查看推理结果和几何校正结果

## 📚 相关文档

- [README.md](README.md) - 完整项目文档
- [MODEL_SETUP.md](MODEL_SETUP.md) - 模型文件配置说明
- [TEST_REPORT.md](TEST_REPORT.md) - 测试报告
- [INSTALLATION_COMPLETE.md](INSTALLATION_COMPLETE.md) - 安装完成报告

---

*最后更新: 2025-01-27*



