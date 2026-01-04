# 推理命令参数修复

## 🔍 问题描述

推理失败，错误信息：
```
sahi_inference.py: error: unrecognized arguments: --conf-threshold 0.25 --overlap-ratio 0.2
```

## ✅ 修复内容

### 问题原因

`docker_client.py` 中使用的参数名称与实际的 `sahi_inference.py` 脚本不匹配：

**错误的参数**:
- `--conf-threshold` ❌
- `--overlap-ratio` ❌

**正确的参数**:
- `--conf` ✅
- `--overlap-height-ratio` ✅
- `--overlap-width-ratio` ✅

### 修复位置

`src/inference/docker_client.py` 第 131-143 行：

**修复前**:
```python
cmd = [
    "python",
    "src/inference/sahi_inference.py",
    "--weights", weights_path,
    "--source", docker_input_path,
    "--output-dir", docker_output_dir,
    "--slice-height", str(slice_height),
    "--slice-width", str(slice_width),
    "--conf-threshold", str(conf_threshold),  # ❌ 错误
    "--overlap-ratio", str(overlap_ratio),   # ❌ 错误
    "--save-img",
    "--save-json",
]
```

**修复后**:
```python
cmd = [
    "python",
    "src/inference/sahi_inference.py",
    "--weights", weights_path,
    "--source", docker_input_path,
    "--output-dir", docker_output_dir,
    "--slice-height", str(slice_height),
    "--slice-width", str(slice_width),
    "--conf", str(conf_threshold),                    # ✅ 正确
    "--overlap-height-ratio", str(overlap_ratio),     # ✅ 正确
    "--overlap-width-ratio", str(overlap_ratio),      # ✅ 正确
    "--save-img",
    "--save-json",
]
```

## 📋 sahi_inference.py 支持的参数

根据帮助信息，脚本支持以下参数：

- `--weights`: 模型权重文件路径
- `--source`: 输入图像路径
- `--output-dir`: 输出目录
- `--slice-height`: 切片高度
- `--slice-width`: 切片宽度
- `--overlap-height-ratio`: 高度方向重叠比例
- `--overlap-width-ratio`: 宽度方向重叠比例
- `--conf`: 置信度阈值
- `--iou`: IoU 阈值
- `--device`: 设备（CPU/GPU）
- `--save-img`: 保存图像
- `--save-json`: 保存 JSON 结果

## ✅ 验证

修复后，推理命令应该可以正常执行。

## 🚀 使用

现在可以重新尝试运行推理：

1. 启动应用: `./run.sh` 或 `python3 -m streamlit run app.py`
2. 上传图像
3. 点击"运行推理"按钮

---

*修复日期: 2025-01-27*

