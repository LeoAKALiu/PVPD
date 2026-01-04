#!/bin/bash
# Streamlit 应用启动脚本

# 使用 python3 -m streamlit 避免路径问题
python3 -m streamlit run app.py "$@"

