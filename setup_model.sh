#!/bin/bash
# 模型文件设置脚本

set -e

MODEL_SOURCE="/Users/leo/code/PVPD/best.pt"
MODEL_DEST="/Users/leo/code/SAHI_inf/pv_pile/runs/detect/train4/weights/best.pt"

echo "=== 模型文件设置 ==="
echo "源文件: $MODEL_SOURCE"
echo "目标: $MODEL_DEST"

# 检查源文件是否存在
if [ ! -f "$MODEL_SOURCE" ]; then
    echo "❌ 错误: 源模型文件不存在: $MODEL_SOURCE"
    exit 1
fi

# 创建目标目录
echo "创建目标目录..."
mkdir -p "$(dirname "$MODEL_DEST")"

# 复制模型文件
echo "复制模型文件..."
cp "$MODEL_SOURCE" "$MODEL_DEST"

# 验证文件
if [ -f "$MODEL_DEST" ]; then
    echo "✅ 模型文件已复制到: $MODEL_DEST"
    ls -lh "$MODEL_DEST"
    
    # 验证容器内文件
    echo ""
    echo "验证容器内文件..."
    docker exec pv_pile_detection ls -lh /app/runs/detect/train4/weights/best.pt 2>&1 || {
        echo "⚠️  警告: 容器内文件验证失败，但文件已复制到宿主机"
        echo "   容器可能需要重启才能看到新文件，或者检查挂载配置"
    }
    
    echo ""
    echo "✅ 设置完成！"
    echo "模型文件路径: /app/runs/detect/train4/weights/best.pt"
else
    echo "❌ 错误: 文件复制失败"
    exit 1
fi

