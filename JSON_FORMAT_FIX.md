# JSON 格式解析修复

## 🔍 问题描述

推理完成后，JSON 解析失败：
```
ValueError: JSON 根对象必须是字典
```

## ✅ 问题原因

实际的 SAHI 输出 JSON 格式是**列表格式**，而不是 COCO 字典格式：

**实际格式**（列表）:
```json
[
  {
    "image_id": 0,
    "bbox": [x, y, width, height],
    "score": 0.687,
    "category_id": 0,
    "category_name": "桩基",
    ...
  },
  ...
]
```

**期望格式**（COCO 字典）:
```json
{
  "annotations": [
    {
      "bbox": [x, y, width, height],
      "score": 0.687,
      "category_id": 0,
      ...
    }
  ]
}
```

## ✅ 修复内容

更新了 `src/inference/result_parser.py` 中的 `parse_sahi_results()` 函数：

1. **支持两种格式**:
   - 列表格式：直接使用列表作为 annotations
   - COCO 格式：从字典中提取 "annotations" 字段

2. **字段名称兼容**:
   - `score` 或 `confidence` 都可以
   - `category_id` 或 `categoryId` 都可以

## 📋 修复后的逻辑

```python
# 验证 JSON 结构并处理不同格式
if isinstance(data, list):
    # 如果根对象是列表，直接使用
    annotations = data
elif isinstance(data, dict):
    # 如果是字典，尝试提取 annotations
    if "annotations" not in data:
        raise KeyError("JSON 缺少 'annotations' 字段")
    annotations = data["annotations"]
else:
    raise ValueError(f"不支持的 JSON 格式")
```

## ✅ 验证

- ✅ 成功解析列表格式 JSON
- ✅ 检测到 236 个检测结果
- ✅ 统计信息计算正常

## 🚀 现在可以正常使用

重新运行推理，JSON 解析应该可以正常工作。

---

*修复日期: 2025-01-27*



