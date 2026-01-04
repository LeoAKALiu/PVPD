"""Streamlit 主应用 - PV Pile Integration System."""

import logging
import streamlit as st
from pathlib import Path
from typing import Optional

import config
from src.geometry.corrector import apply_geometric_correction
from src.inference.docker_client import check_container_status, run_docker_inference
from src.inference.result_parser import get_detection_stats, parse_sahi_results
from src.visualization.confidence_colors import get_confidence_emoji
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

# 自定义 CSS 样式（治愈系配色）
st.markdown(
    """
    <style>
    /* 主色调 - 治愈系绿色 */
    .main {
        background-color: #F8FFF8;
    }
    
    /* 卡片样式 */
    .stMetric {
        background-color: #FFFFFF;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* 按钮样式 */
    .stButton > button {
        background-color: #58CC02;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #4CAF00;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(88, 204, 2, 0.3);
    }
    
    /* 成功消息样式 */
    .stSuccess {
        background-color: #E8F5E9;
        border-left: 4px solid #58CC02;
        padding: 1rem;
        border-radius: 5px;
    }
    
    /* 错误消息样式 */
    .stError {
        background-color: #FFEBEE;
        border-left: 4px solid #F44336;
        padding: 1rem;
        border-radius: 5px;
    }
    
    /* 信息框样式 */
    .stInfo {
        background-color: #E3F2FD;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """主应用函数."""
    st.title("🔋 PV Pile Integration System")
    st.markdown("光伏板桩基检测集成系统 - 整合 PV Pile 和 SolarGeoFix")
    
    # 侧边栏 - 参数配置
    with st.sidebar:
        st.header("⚙️ 配置参数")
        
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
        st.subheader("🔧 几何校正参数")
        
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
    st.header("📤 图像上传")
    
    uploaded_file = st.file_uploader(
        "选择无人机正摄航拍图像",
        type=["png", "jpg", "jpeg"],
        help="支持 PNG 和 JPG 格式"
    )
    
    if uploaded_file is not None:
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
        st.header("📷 原始图像")
        st.image(uploaded_file, use_container_width=True)
        
        # 推理按钮
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            run_inference = st.button("🚀 运行推理", type="primary", use_container_width=True)
        with col2:
            clear_cache = st.button("🗑️ 清除缓存", use_container_width=True)
        
        if clear_cache:
            st.cache_data.clear()
            st.success("缓存已清除")
        
        # 检查容器状态
        container_status = check_container_status()
        if not container_status:
            st.error(
                f"⚠️ Docker 容器 '{config.CONTAINER_NAME}' 未运行。"
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
                            use_ransac=use_ransac,
                            use_grid_fill=use_grid_fill,
                            ransac_degree=ransac_degree,
                            ransac_threshold=ransac_threshold,
                            grid_spacing=grid_spacing,
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
                        
                        st.success(
                            f"✅ 推理完成！检测到 {stats['total']} 个目标，"
                            f"几何校正后 {corrected_stats['total']} 个目标"
                        )
                        
                    except Exception as e:
                        logger.exception("推理失败")
                        st.error(f"❌ 推理失败: {str(e)}")
        
        # 显示推理结果
        if "detections" in st.session_state and st.session_state["detections"]:
            detections = st.session_state["detections"]
            stats = st.session_state["stats"]
            input_path = st.session_state["input_path"]
            
            # 推理结果可视化
            st.header("🔍 推理结果")
            
            # 统计信息
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总检测数", stats["total"])
            with col2:
                st.metric(
                    f"{get_confidence_emoji(0.8)} 高置信度",
                    stats["high_confidence"],
                )
            with col3:
                st.metric(
                    f"{get_confidence_emoji(0.5)} 中置信度",
                    stats["medium_confidence"],
                )
            with col4:
                st.metric(
                    f"{get_confidence_emoji(0.3)} 低置信度",
                    stats["low_confidence"],
                )
            
            st.metric("平均置信度", f"{stats['avg_confidence']:.3f}")
            
            # 创建可视化图像
            try:
                vis_image = create_visualization(
                    image_path=input_path,
                    detections=detections,
                    thickness=2,
                    show_label=True,
                    show_confidence=True,
                )
                
                # 转换为 PIL 图像用于 Streamlit 显示
                pil_image = image_to_pil(vis_image)
                
                # 显示可视化结果
                st.image(pil_image, use_container_width=True, caption="推理结果可视化")
                
                # 下载按钮
                from io import BytesIO
                import json
                
                col1, col2 = st.columns(2)
                
                with col1:
                    buf = BytesIO()
                    pil_image.save(buf, format="PNG")
                    st.download_button(
                        label="📥 下载推理结果图像",
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
                        label="📄 导出 JSON 结果",
                        data=json_str.encode("utf-8"),
                        file_name=f"{Path(input_path).stem}_inference.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                
            except Exception as e:
                logger.exception("可视化失败")
                st.error(f"可视化失败: {str(e)}")
        
        # 几何校正结果
        st.header("✅ 几何校正结果")
        if "corrected_detections" in st.session_state:
            corrected_detections = st.session_state["corrected_detections"]
            corrected_stats = st.session_state["corrected_stats"]
            correction_stats = st.session_state["correction_stats"]
            input_path = st.session_state["input_path"]
            
            # 校正统计信息
            st.subheader("📊 校正统计")
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
            st.subheader("📈 校正后统计")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总检测数", corrected_stats["total"])
            with col2:
                st.metric(
                    f"{get_confidence_emoji(0.8)} 高置信度",
                    corrected_stats["high_confidence"],
                )
            with col3:
                st.metric(
                    f"{get_confidence_emoji(0.5)} 中置信度",
                    corrected_stats["medium_confidence"],
                )
            with col4:
                st.metric(
                    f"{get_confidence_emoji(0.3)} 低置信度",
                    corrected_stats["low_confidence"],
                )
            
            st.metric("平均置信度", f"{corrected_stats['avg_confidence']:.3f}")
            
            # 创建校正后的可视化图像
            try:
                corrected_vis_image = create_visualization(
                    image_path=input_path,
                    detections=corrected_detections,
                    thickness=2,
                    show_label=True,
                    show_confidence=True,
                )
                
                # 转换为 PIL 图像用于 Streamlit 显示
                corrected_pil_image = image_to_pil(corrected_vis_image)
                
                # 显示校正后的可视化结果
                st.subheader("🖼️ 校正后可视化")
                st.image(
                    corrected_pil_image,
                    use_container_width=True,
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
                        label="📥 下载校正结果图像",
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
                        label="📄 导出校正 JSON 结果",
                        data=json_str.encode("utf-8"),
                        file_name=f"{Path(input_path).stem}_corrected.json",
                        mime="application/json",
                        use_container_width=True,
                    )
                
            except Exception as e:
                logger.exception("校正结果可视化失败")
                st.error(f"校正结果可视化失败: {str(e)}")
        elif "detections" in st.session_state:
            st.info("几何校正已完成，但结果未保存到 session state")
        else:
            st.info("请先运行推理以查看几何校正结果")
    
    else:
        st.info("👆 请上传一张图像开始处理")


if __name__ == "__main__":
    main()

