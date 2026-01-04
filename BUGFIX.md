# Bug 修复记录

## 修复: Streamlit image() 参数错误

### 问题描述
```
TypeError: ImageMixin.image() got an unexpected keyword argument 'use_container_width'
```

### 原因
Streamlit 1.38.0 版本的 `st.image()` 函数使用 `use_column_width` 参数，而不是 `use_container_width`。

### 修复
将所有 `st.image()` 调用中的 `use_container_width=True` 改为 `use_column_width=True`。

### 修复位置
- `app.py` 第 210 行：原始图像显示
- `app.py` 第 335 行：推理结果可视化
- `app.py` 第 437-439 行：几何校正结果可视化

**注意**: 所有 `st.image()` 调用现在都使用 `use_column_width=True` 以保持一致性。

### 验证
- ✅ 代码语法检查通过
- ✅ 模块导入成功

---

*修复日期: 2025-01-27*

