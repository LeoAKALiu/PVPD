# Docker 连接问题排查指南

## 🔍 问题描述

应用显示 Docker 容器未运行，但实际上容器正在运行。错误信息：
```
Docker 错误: Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory'))
```

## ✅ 解决方案

### 问题原因

Python `docker` 库无法连接到 Docker daemon，但 Docker 命令行工具可以正常工作。这通常发生在：
1. Docker Desktop 的 socket 路径与 Python 库期望的不同
2. Docker Desktop 使用不同的上下文（如 `desktop-linux`）

### 已实施的修复

代码已更新，添加了**备用检查机制**：

1. **容器状态检查** (`check_container_status`):
   - 首先尝试使用 Docker API
   - 如果失败，自动切换到命令行检查 (`docker ps`)
   - 确保即使 API 不可用也能正确检测容器状态

2. **推理执行** (`run_docker_inference`):
   - 首先尝试使用 Docker API (`container.exec_run`)
   - 如果失败，自动切换到命令行方式 (`docker exec`)
   - 保持功能完整性

### 验证修复

运行以下命令验证：

```bash
# 检查容器状态（应该返回"运行中"）
python3 -c "from src.inference.docker_client import check_container_status; print('运行中' if check_container_status() else '未运行')"
```

## 🚀 使用应用

现在可以正常启动应用：

```bash
# 启动应用
./run.sh
# 或
python3 -m streamlit run app.py
```

应用会自动使用备用方案检查容器状态和执行推理。

## 📝 技术细节

### Docker API vs 命令行

- **Docker API**: 使用 Python `docker` 库，需要连接到 Docker socket
- **命令行**: 使用 `subprocess` 调用 `docker` 命令，更可靠

### 为什么命令行更可靠？

1. Docker 命令行工具会自动处理不同的 Docker 上下文
2. 不依赖于特定的 socket 路径
3. 与系统 Docker 配置完全兼容

## ⚠️ 注意事项

1. **性能**: 命令行方式可能稍慢，但功能完全相同
2. **错误处理**: 两种方式都有完整的错误处理
3. **日志**: 会记录使用的是 API 还是命令行方式

## 🔧 如果问题仍然存在

如果应用仍然无法检测到容器，请检查：

1. **容器是否真的在运行**:
   ```bash
   docker ps | grep pv_pile
   ```

2. **Docker 命令行是否可用**:
   ```bash
   docker --version
   docker ps
   ```

3. **容器名称是否正确**:
   ```bash
   # 检查配置
   python3 -c "import config; print(config.CONTAINER_NAME)"
   
   # 检查实际容器名
   docker ps --format "{{.Names}}"
   ```

---

*最后更新: 2025-01-27*



