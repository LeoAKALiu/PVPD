# Docker 模型文件配置指南

## 📋 当前容器状态

容器 `pv_pile_detection` 已在运行，已挂载以下目录：
- `/Users/leo/code/SAHI_inf/pv_pile/data` -> `/app/data`
- `/Users/leo/code/SAHI_inf/pv_pile/weights` -> `/app/weights`
- `/Users/leo/code/SAHI_inf/pv_pile/runs` -> `/app/runs`

## 🔧 模型文件配置方案

### 方案 1: 复制模型文件到已挂载的目录（推荐，最简单）

如果容器已挂载了 `/app/runs` 目录，可以直接将模型文件复制到对应位置：

```bash
# 复制模型文件到已挂载的 runs 目录
cp /Users/leo/code/PVPD/best.pt /Users/leo/code/SAHI_inf/pv_pile/runs/detect/train4/weights/best.pt

# 确保目录存在
mkdir -p /Users/leo/code/SAHI_inf/pv_pile/runs/detect/train4/weights

# 然后复制文件
cp /Users/leo/code/PVPD/best.pt /Users/leo/code/SAHI_inf/pv_pile/runs/detect/train4/weights/best.pt

# 验证文件已复制
docker exec pv_pile_detection ls -lh /app/runs/detect/train4/weights/best.pt
```

**优点**: 不需要重启容器，立即生效

### 方案 2: 使用容器内已有的模型路径

如果容器内已经有模型文件，更新配置文件使用现有路径：

```bash
# 检查容器内模型文件位置
docker exec pv_pile_detection find /app -name "*.pt" -type f

# 如果找到模型文件，更新 config.py 或设置环境变量
export PV_PILE_MODEL_WEIGHTS="/app/runs/detect/train4/weights/best.pt"
# 或使用其他找到的路径
```

### 方案 3: 重新启动容器并添加新挂载（需要停止容器）

如果需要添加新的挂载点，需要重新启动容器：

```bash
# 1. 停止当前容器
docker stop pv_pile_detection

# 2. 删除容器（保留镜像）
docker rm pv_pile_detection

# 3. 重新启动容器并添加模型文件挂载
# 注意：需要知道原始容器的启动命令，这里只是示例
docker run -d \
  --name pv_pile_detection \
  -v /Users/leo/code/SAHI_inf/pv_pile/data:/app/data \
  -v /Users/leo/code/SAHI_inf/pv_pile/weights:/app/weights \
  -v /Users/leo/code/SAHI_inf/pv_pile/runs:/app/runs \
  -v /Users/leo/code/PVPD/best.pt:/app/models/best.pt \
  -v /Users/leo/code/PVPD/input:/app/input \
  -v /Users/leo/code/PVPD/output:/app/output \
  pv_pile:latest

# 或者如果使用 docker-compose，修改 docker-compose.yml 添加：
# volumes:
#   - ./best.pt:/app/models/best.pt
```

**注意**: 需要知道原始容器的完整启动参数

### 方案 4: 使用 Docker cp 命令（临时方案）

如果只是临时测试，可以使用 `docker cp` 复制文件到容器：

```bash
# 复制模型文件到容器
docker cp /Users/leo/code/PVPD/best.pt pv_pile_detection:/app/models/best.pt

# 验证文件已复制
docker exec pv_pile_detection ls -lh /app/models/best.pt
```

**注意**: 容器重启后文件会丢失，需要重新复制

## ✅ 推荐方案

**推荐使用方案 1**，因为：
1. 不需要重启容器
2. 利用已有的挂载点
3. 文件持久化（在宿主机上）
4. 最简单快捷

## 🔍 验证配置

配置完成后，验证模型文件是否可访问：

```bash
# 检查容器内模型文件
docker exec pv_pile_detection ls -lh /app/runs/detect/train4/weights/best.pt

# 或检查新挂载的路径
docker exec pv_pile_detection ls -lh /app/models/best.pt

# 验证应用配置
python3 -c "import config; print(f'模型路径: {config.MODEL_WEIGHTS}')"
```

## 📝 更新配置文件

根据选择的方案，可能需要更新 `config.py` 中的 `MODEL_WEIGHTS` 路径：

```python
# 如果使用方案 1（复制到 runs 目录）
MODEL_WEIGHTS = "/app/runs/detect/train4/weights/best.pt"

# 如果使用方案 3 或 4（挂载到 /app/models）
MODEL_WEIGHTS = "/app/models/best.pt"
```

---

*最后更新: 2025-01-27*



