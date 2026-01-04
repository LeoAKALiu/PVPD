"""Streamlit 主应用 - PV Pile Integration System."""

import logging
import streamlit as st
from pathlib import Path
from typing import Optional

import config
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
                        
                        # 保存结果到 session state
                        st.session_state["detections"] = detections
                        st.session_state["stats"] = stats
                        st.session_state["result"] = result
                        st.session_state["input_path"] = input_path
                        
                        st.success(f"✅ 推理完成！检测到 {stats['total']} 个目标")
                        
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
                
                buf = BytesIO()
                pil_image.save(buf, format="PNG")
                st.download_button(
                    label="📥 下载推理结果图像",
                    data=buf.getvalue(),
                    file_name=f"{Path(input_path).stem}_inference.png",
                    mime="image/png",
                )
                
            except Exception as e:
                logger.exception("可视化失败")
                st.error(f"可视化失败: {str(e)}")
        
        # 几何校正结果（占位）
        st.header("✅ 几何校正结果")
        if "detections" in st.session_state:
            st.info("几何校正功能将在 Phase 4 中实现")
        else:
            st.info("请先运行推理以查看几何校正结果")
    
    else:
        st.info("👆 请上传一张图像开始处理")


if __name__ == "__main__":
    main()

