"""Streamlit 主应用 - PV Pile Integration System."""

import logging
import streamlit as st
from pathlib import Path
from typing import Optional

import config
from src.geometry.corrector import apply_geometric_correction
from src.inference.docker_client import check_container_status, run_docker_inference
from src.inference.result_parser import get_detection_stats, parse_sahi_results
from src.visualization.image_stitcher import create_visualization, image_to_pil

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 页面配置
st.set_page_config(
    page_title=config.STREAMLIT_PAGE_TITLE,
    page_icon=config.STREAMLIT_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# 确保必要的目录存在
config.ensure_directories()

# 自定义 CSS 样式（MagicUI 专业设计风格）
st.markdown(
    """
    <style>
    /* MagicUI 专业设计风格 */
    .main {
        background-color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    /* 标题样式 */
    h1 {
        color: #0f172a;
        font-weight: 700;
        letter-spacing: -0.025em;
    }
    
    h2, h3 {
        color: #1e293b;
        font-weight: 600;
        letter-spacing: -0.015em;
    }
    
    /* 卡片样式 */
    .stMetric {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        transition: all 0.2s;
    }
    
    .stMetric:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-color: #cbd5e1;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background-color: #0f172a;
        color: white;
        border-radius: 0.5rem;
        border: none;
        font-weight: 500;
        padding: 0.625rem 1.25rem;
        transition: all 0.2s;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    .stButton > button:hover {
        background-color: #1e293b;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* 成功消息样式 */
    .stSuccess {
        background-color: #f0fdf4;
        border: 1px solid #86efac;
        color: #166534;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* 错误消息样式 */
    .stError {
        background-color: #fef2f2;
        border: 1px solid #fca5a5;
        color: #991b1b;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* 信息框样式 */
    .stInfo {
        background-color: #eff6ff;
        border: 1px solid #93c5fd;
        color: #1e40af;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    
    /* 确保侧边栏内容区域背景正确 */
    [data-testid="stSidebar"] > div {
        background-color: #f8fafc;
    }
    
    /* 确保主内容区域背景正确 */
    .main .block-container {
        background-color: #ffffff;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 0.5rem;
        border: 1px solid #cbd5e1;
        padding: 0.5rem 0.75rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #0f172a;
        box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.1);
    }
    
    /* 滑块样式 - 移除可能导致黑色块的样式，使用 Streamlit 默认样式 */
    
    /* 文件上传样式 */
    .stFileUploader > div {
        border: 2px dashed #cbd5e1;
        border-radius: 0.5rem;
        padding: 1.5rem;
        background-color: #f8fafc;
        transition: all 0.2s;
    }
    
    .stFileUploader > div:hover {
        border-color: #0f172a;
        background-color: #f1f5f9;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """主应用函数."""
    st.title("PV Pile Integration System")
    st.markdown("光伏板桩基检测集成系统 - 整合 PV Pile 和 SolarGeoFix")
    
    # 侧边栏 - 参数配置
    with st.sidebar:
        st.header("配置参数")
        
        slice_height = st.number_input(
            "切片高度",
            min_value=128,
            max_value=2048,
            value=config.DEFAULT_SLICE_HEIGHT,
            step=64,
            help="SAHI 切片的像素高度"
        )
        
        slice_width = st.number_input(
            "切片宽度",
            min_value=128,
            max_value=2048,
            value=config.DEFAULT_SLICE_WIDTH,
            step=64,
            help="SAHI 切片的像素宽度"
        )
        
        conf_threshold = st.slider(
            "置信度阈值",
            min_value=0.0,
            max_value=1.0,
            value=config.DEFAULT_CONF_THRESHOLD,
            step=0.05,
            help="检测结果的最小置信度"
        )
        
        overlap_ratio = st.slider(
            "重叠比例",
            min_value=0.0,
            max_value=0.5,
            value=config.DEFAULT_OVERLAP_RATIO,
            step=0.05,
            help="切片之间的重叠比例"
        )
        
        st.divider()
        st.subheader("几何校正参数")
        
        use_chain_search = st.checkbox(
            "使用链式搜索算法（推荐）",
            value=False,
            help="使用链式搜索算法识别桩列，适合复杂场景（多列、弯曲）"
        )
        
        if not use_chain_search:
            use_ransac = st.checkbox(
                "使用 RANSAC 回归",
                value=True,
                help="使用 RANSAC 回归修正检测点位置"
            )
            
            use_grid_fill = st.checkbox(
                "使用网格填充",
                value=True,
                help="使用网格填充算法生成缺失的检测点"
            )
        else:
            use_ransac = False
            use_grid_fill = False
        
        if use_ransac:
            ransac_degree = st.slider(
                "RANSAC 多项式次数",
                min_value=1,
                max_value=3,
                value=2,
                help="RANSAC 回归的多项式次数"
            )
            
            ransac_threshold = st.slider(
                "RANSAC 残差阈值",
                min_value=1.0,
                max_value=50.0,
                value=10.0,
                step=1.0,
                help="RANSAC 回归的残差阈值"
            )
        else:
            ransac_degree = 2
            ransac_threshold = 10.0
        
        if use_grid_fill:
            grid_spacing = st.slider(
                "网格间距",
                min_value=20.0,
                max_value=200.0,
                value=50.0,
                step=10.0,
                help="网格填充的间距（像素）"
            )
        else:
            grid_spacing = 50.0
    
    # 主内容区
    st.header("图像上传")
    
    uploaded_file = st.file_uploader(
        "选择无人机正摄航拍图像",
        type=["png", "jpg", "jpeg"],
        help="支持 PNG 和 JPG 格式"
    )
    
    if uploaded_file is not None:
        # 检查是否是新图像（与 session state 中保存的图像不同）
        current_file_name = uploaded_file.name
        if "current_file_name" not in st.session_state:
            st.session_state["current_file_name"] = None
        
        # 如果图像发生变化，清除所有相关的 session state
        if st.session_state["current_file_name"] != current_file_name:
            # 清除旧的推理结果
            keys_to_clear = [
                "detections",
                "stats",
                "corrected_detections",
                "corrected_stats",
                "correction_stats",
                "result",
                "input_path",
                "image_shape",
            ]
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # 更新当前文件名
            st.session_state["current_file_name"] = current_file_name
        
        # 显示上传的图像信息
        file_details = {
            "文件名": uploaded_file.name,
            "文件类型": uploaded_file.type,
            "文件大小": f"{uploaded_file.size / 1024 / 1024:.2f} MB"
        }
        st.json(file_details)
        
        # 保存上传的文件
        input_path = config.INPUT_DIR / uploaded_file.name
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 显示原图
        st.header("原始图像")
        st.image(uploaded_file, use_column_width=True)
        
        # 推理按钮
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            run_inference = st.button("运行推理", type="primary", use_container_width=True)
        with col2:
            clear_cache = st.button("清除缓存", use_container_width=True)
        
        if clear_cache:
            st.cache_data.clear()
            st.success("缓存已清除")
        
        # 检查容器状态
        container_status = check_container_status()
        if not container_status:
            st.error(
                f"Docker 容器 '{config.CONTAINER_NAME}' 未运行。"
                "请先启动容器。"
            )
        
        # 运行推理
        if run_inference:
            if not container_status:
                st.error("无法运行推理：容器未运行")
            else:
                with st.spinner("正在运行推理，请稍候..."):
                    try:
                        # 运行 Docker 推理
                        output_dir = config.OUTPUT_DIR
                        result = run_docker_inference(
                            image_path=input_path,
                            output_dir=output_dir,
                            slice_height=slice_height,
                            slice_width=slice_width,
                            conf_threshold=conf_threshold,
                            overlap_ratio=overlap_ratio,
                        )
                        
                        # 解析结果
                        detections = parse_sahi_results(result["json_path"])
                        stats = get_detection_stats(detections)
                        
                        # 获取图像尺寸用于几何校正
                        import cv2
                        image = cv2.imread(str(input_path))
                        image_shape = image.shape[:2]  # (height, width)
                        
                        # 应用几何校正
                        corrected_detections, correction_stats = apply_geometric_correction(
                            detections=detections,
                            image_shape=image_shape,
                            use_chain_search=use_chain_search,
                            use_ransac=use_ransac if not use_chain_search else False,
                            use_grid_fill=use_grid_fill if not use_chain_search else False,
                            ransac_degree=ransac_degree if not use_chain_search else 2,
                            ransac_threshold=ransac_threshold if not use_chain_search else 10.0,
                            grid_spacing=grid_spacing if not use_chain_search else 50.0,
                        )
                        
                        corrected_stats = get_detection_stats(corrected_detections)
                        
                        # 保存结果到 session state
                        st.session_state["detections"] = detections
                        st.session_state["stats"] = stats
                        st.session_state["corrected_detections"] = corrected_detections
                        st.session_state["corrected_stats"] = corrected_stats
                        st.session_state["correction_stats"] = correction_stats
                        st.session_state["result"] = result
                        st.session_state["input_path"] = input_path
                        st.session_state["image_shape"] = image_shape
                        st.session_state["current_file_name"] = current_file_name  # 确保保存当前文件名
                        
                        st.success(
                            f"推理完成！检测到 {stats['total']} 个目标，"
                            f"几何校正后 {corrected_stats['total']} 个目标"
                        )
                        
                    except Exception as e:
                        logger.exception("推理失败")
                        st.error(f"推理失败: {str(e)}")
        
        # 显示推理结果（只显示当前图像的推理结果）
        if (
            "detections" in st.session_state
            and st.session_state["detections"]
            and "current_file_name" in st.session_state
            and st.session_state["current_file_name"] == current_file_name
        ):
            detections = st.session_state["detections"]
            stats = st.session_state["stats"]
            input_path = st.session_state["input_path"]
            
            # 推理结果可视化
            st.header("推理结果")
            
            # 统计信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总检测数", stats["total"])
            with col2:
                st.metric("高置信度", stats["high_confidence"])
            with col3:
                st.metric("中置信度", stats["medium_confidence"])
            with col4:
                st.metric("低置信度", stats["low_confidence"])
            
            st.metric("平均置信度", f"{stats['avg_confidence']:.3f}")
            
            # 创建可视化图像
            try:
                vis_image = create_visualization(
                    image_path=input_path,
                    detections=detections,
                    thickness=2,
                    show_label=False,
                    show_confidence=False,
                )
                
                # 转换为 PIL 图像用于 Streamlit 显示
                pil_image = image_to_pil(vis_image)
                
                # 显示可视化结果
                st.image(pil_image, use_column_width=True, caption="推理结果可视化")
                
                # 下载按钮
                from io import BytesIO
                import json
                
                col1, col2 = st.columns(2)
                
                with col1:
                    buf = BytesIO()
                    pil_image.save(buf, format="PNG")
                    st.download_button(
                        label="下载推理结果图像",
                        data=buf.getvalue(),
                        file_name=f"{Path(input_path).stem}_inference.png",
                        mime="image/png",
                        use_container_width=True,
                    )
                
                with col2:
                    # 导出 JSON 结果
                    json_data = {
                        "image": str(input_path),
                        "detections": [det.to_dict() for det in detections],
                        "stats": stats,
                    }
                    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="导出 JSON 结果",
                        data=json_str.encode("utf-8"),
                        file_name=f"{Path(input_path).stem}_inference.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                
            except Exception as e:
                logger.exception("可视化失败")
                st.error(f"可视化失败: {str(e)}")
        
        # 几何校正结果（只显示当前图像的校正结果）
        st.header("几何校正结果")
        if (
            "corrected_detections" in st.session_state
            and "current_file_name" in st.session_state
            and st.session_state["current_file_name"] == current_file_name
        ):
            corrected_detections = st.session_state["corrected_detections"]
            corrected_stats = st.session_state["corrected_stats"]
            correction_stats = st.session_state["correction_stats"]
            input_path = st.session_state["input_path"]
            
            # 校正统计信息
            st.subheader("校正统计")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("原始检测数", correction_stats["original_count"])
            with col2:
                st.metric("校正后检测数", correction_stats["corrected_count"])
            with col3:
                delta = correction_stats["added_count"] - correction_stats["removed_count"]
                st.metric(
                    "变化",
                    f"{delta:+d}",
                    delta=delta,
                )
            with col4:
                st.metric("新增检测", correction_stats["added_count"])
            
            # 校正后统计信息
            st.subheader("校正后统计")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总检测数", corrected_stats["total"])
            with col2:
                st.metric("高置信度", corrected_stats["high_confidence"])
            with col3:
                st.metric("中置信度", corrected_stats["medium_confidence"])
            with col4:
                st.metric("低置信度", corrected_stats["low_confidence"])
            
            st.metric("平均置信度", f"{corrected_stats['avg_confidence']:.3f}")
            
            # 创建校正后的可视化图像
            try:
                corrected_vis_image = create_visualization(
                    image_path=input_path,
                    detections=corrected_detections,
                    thickness=2,
                    show_label=False,
                    show_confidence=False,
                )
                
                # 转换为 PIL 图像用于 Streamlit 显示
                corrected_pil_image = image_to_pil(corrected_vis_image)
                
                # 显示校正后的可视化结果
                st.subheader("校正后可视化")
                st.image(
                    corrected_pil_image,
                    use_column_width=True,
                    caption="几何校正后的检测结果",
                )
                
                # 下载按钮
                from io import BytesIO
                import json
                
                col1, col2 = st.columns(2)
                
                with col1:
                    buf = BytesIO()
                    corrected_pil_image.save(buf, format="PNG")
                    st.download_button(
                        label="下载校正结果图像",
                        data=buf.getvalue(),
                        file_name=f"{Path(input_path).stem}_corrected.png",
                        mime="image/png",
                        use_container_width=True,
                    )
                
                with col2:
                    # 导出 JSON 结果
                    json_data = {
                        "image": str(input_path),
                        "original_detections": [det.to_dict() for det in st.session_state["detections"]],
                        "corrected_detections": [det.to_dict() for det in corrected_detections],
                        "correction_stats": correction_stats,
                        "corrected_stats": corrected_stats,
                    }
                    json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="导出校正 JSON 结果",
                        data=json_str.encode("utf-8"),
                        file_name=f"{Path(input_path).stem}_corrected.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                
            except Exception as e:
                logger.exception("校正结果可视化失败")
                st.error(f"校正结果可视化失败: {str(e)}")
        elif (
            "detections" in st.session_state
            and "current_file_name" in st.session_state
            and st.session_state["current_file_name"] == current_file_name
        ):
            st.info("几何校正已完成，但结果未保存到 session state")
        else:
            # 不显示任何信息，因为可能是旧图像的结果
            pass
    
    else:
        st.info("请上传一张图像开始处理")


if __name__ == "__main__":
    main()

