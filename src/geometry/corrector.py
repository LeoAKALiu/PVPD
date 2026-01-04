"""几何校正模块 - 使用 RANSAC 回归和网格填充算法修正检测结果."""

import logging
from typing import Any

import numpy as np
from sklearn.linear_model import RANSACRegressor
from sklearn.preprocessing import PolynomialFeatures

from src.inference.models import Detection

# 配置日志
logger = logging.getLogger(__name__)


def detections_to_sgf_format(detections: list[Detection]) -> list[dict[str, float]]:
    """
    将检测结果列表转换为 SolarGeoFix 格式.
    
    Args:
        detections: 检测结果列表
        
    Returns:
        SolarGeoFix 格式的检测结果列表
    """
    return [det.to_sgf_format() for det in detections]


def sgf_format_to_detections(
    sgf_data: list[dict[str, float]], category_id: int = 0
) -> list[Detection]:
    """
    将 SolarGeoFix 格式转换为检测结果列表.
    
    Args:
        sgf_data: SolarGeoFix 格式的检测结果列表
        category_id: 类别 ID（默认 0）
        
    Returns:
        检测结果列表
    """
    detections = []
    
    for item in sgf_data:
        x_center = item["x_center"]
        y_center = item["y_center"]
        width = item["width"]
        height = item["height"]
        confidence = item.get("confidence", 0.5)
        
        # 转换为 COCO 格式 bbox [x, y, width, height]
        x = x_center - width / 2.0
        y = y_center - height / 2.0
        
        detection = Detection(
            bbox=[x, y, width, height],
            confidence=confidence,
            category_id=category_id,
        )
        
        detections.append(detection)
    
    return detections


def fit_grid_with_ransac(
    points: np.ndarray,
    degree: int = 2,
    residual_threshold: float = 10.0,
    max_trials: int = 100,
) -> tuple[Any, np.ndarray]:
    """
    使用 RANSAC 回归拟合网格.
    
    Args:
        points: 点坐标数组，形状为 (n_points, 2)，每行为 (x, y)
        degree: 多项式次数（默认 2，表示二次拟合）
        residual_threshold: 残差阈值
        max_trials: 最大迭代次数
        
    Returns:
        (拟合模型, 拟合后的点坐标)
    """
    if len(points) < 3:
        logger.warning("点数不足，无法进行 RANSAC 拟合")
        return None, points
    
    # 分离 x 和 y 坐标
    x = points[:, 0].reshape(-1, 1)
    y = points[:, 1]
    
    # 创建多项式特征
    poly_features = PolynomialFeatures(degree=degree, include_bias=True)
    x_poly = poly_features.fit_transform(x)
    
    # 使用 RANSAC 回归
    ransac = RANSACRegressor(
        residual_threshold=residual_threshold,
        max_trials=max_trials,
        random_state=42,
    )
    
    ransac.fit(x_poly, y)
    
    # 预测拟合后的 y 坐标
    y_pred = ransac.predict(x_poly)
    
    # 构建拟合后的点坐标
    fitted_points = np.column_stack([x.flatten(), y_pred])
    
    return ransac, fitted_points


def fill_grid(
    points: np.ndarray,
    image_shape: tuple[int, int],
    grid_spacing: float = 50.0,
) -> np.ndarray:
    """
    使用网格填充算法生成缺失的检测点.
    
    Args:
        points: 现有点坐标数组，形状为 (n_points, 2)
        image_shape: 图像尺寸 (height, width)
        grid_spacing: 网格间距（像素）
        
    Returns:
        填充后的点坐标数组
    """
    height, width = image_shape
    
    # 创建网格
    x_grid = np.arange(0, width, grid_spacing)
    y_grid = np.arange(0, height, grid_spacing)
    
    # 生成网格点
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])
    
    # 过滤掉超出图像边界的点
    valid_mask = (
        (grid_points[:, 0] >= 0)
        & (grid_points[:, 0] < width)
        & (grid_points[:, 1] >= 0)
        & (grid_points[:, 1] < height)
    )
    grid_points = grid_points[valid_mask]
    
    # 如果没有现有点，直接返回网格点
    if len(points) == 0:
        return grid_points
    
    # 计算每个网格点到最近现有点的距离
    from scipy.spatial.distance import cdist
    
    distances = cdist(grid_points, points)
    min_distances = np.min(distances, axis=1)
    
    # 只保留距离现有点足够远的网格点（避免重复）
    # 同时保留距离较近的点（可能缺失的检测）
    threshold = grid_spacing * 0.7
    new_points_mask = min_distances > threshold
    
    # 添加新点
    new_points = grid_points[new_points_mask]
    
    if len(new_points) > 0:
        # 合并现有点和新点
        all_points = np.vstack([points, new_points])
    else:
        all_points = points
    
    return all_points


def apply_geometric_correction(
    detections: list[Detection],
    image_shape: tuple[int, int],
    use_ransac: bool = True,
    use_grid_fill: bool = True,
    ransac_degree: int = 2,
    ransac_threshold: float = 10.0,
    grid_spacing: float = 50.0,
) -> tuple[list[Detection], dict[str, Any]]:
    """
    应用几何校正到检测结果.
    
    Args:
        detections: 原始检测结果列表
        image_shape: 图像尺寸 (height, width)
        use_ransac: 是否使用 RANSAC 回归
        use_grid_fill: 是否使用网格填充
        ransac_degree: RANSAC 多项式次数
        ransac_threshold: RANSAC 残差阈值
        grid_spacing: 网格填充间距
        
    Returns:
        (校正后的检测结果列表, 统计信息字典)
    """
    if not detections:
        logger.warning("检测结果为空，跳过几何校正")
        return [], {
            "original_count": 0,
            "corrected_count": 0,
            "added_count": 0,
            "removed_count": 0,
        }
    
    original_count = len(detections)
    logger.info(f"开始几何校正，原始检测数: {original_count}")
    
    # 提取中心点坐标
    points = np.array([[det.x_center, det.y_center] for det in detections])
    
    corrected_points = points.copy()
    
    # RANSAC 回归校正
    if use_ransac and len(points) >= 3:
        try:
            ransac_model, fitted_points = fit_grid_with_ransac(
                points,
                degree=ransac_degree,
                residual_threshold=ransac_threshold,
            )
            
            if ransac_model is not None:
                corrected_points = fitted_points
                logger.info("RANSAC 回归完成")
        except Exception as e:
            logger.warning(f"RANSAC 回归失败: {e}，使用原始点")
    
    # 网格填充
    if use_grid_fill:
        try:
            filled_points = fill_grid(corrected_points, image_shape, grid_spacing)
            
            if len(filled_points) > len(corrected_points):
                corrected_points = filled_points
                logger.info(
                    f"网格填充完成，新增 {len(filled_points) - len(corrected_points)} 个点"
                )
        except Exception as e:
            logger.warning(f"网格填充失败: {e}，使用校正后的点")
    
    # 构建校正后的检测结果
    corrected_detections: list[Detection] = []
    
    # 保留原始检测的置信度和类别信息
    for i, point in enumerate(corrected_points):
        if i < len(detections):
            # 使用原始检测的信息
            original_det = detections[i]
            x_center, y_center = point[0], point[1]
            
            # 更新中心点，保持原始尺寸
            x = x_center - original_det.bbox[2] / 2.0
            y = y_center - original_det.bbox[3] / 2.0
            
            corrected_det = Detection(
                bbox=[x, y, original_det.bbox[2], original_det.bbox[3]],
                confidence=original_det.confidence,
                category_id=original_det.category_id,
                category_name=original_det.category_name,
                x_center=x_center,
                y_center=y_center,
            )
        else:
            # 新增的检测点，使用默认值
            x_center, y_center = point[0], point[1]
            default_width = 50.0  # 默认宽度
            default_height = 50.0  # 默认高度
            x = x_center - default_width / 2.0
            y = y_center - default_height / 2.0
            
            corrected_det = Detection(
                bbox=[x, y, default_width, default_height],
                confidence=0.5,  # 默认置信度
                category_id=0,
            )
        
        corrected_detections.append(corrected_det)
    
    corrected_count = len(corrected_detections)
    added_count = max(0, corrected_count - original_count)
    removed_count = max(0, original_count - corrected_count)
    
    stats = {
        "original_count": original_count,
        "corrected_count": corrected_count,
        "added_count": added_count,
        "removed_count": removed_count,
    }
    
    logger.info(
        f"几何校正完成: 原始 {original_count} -> 校正后 {corrected_count} "
        f"(新增 {added_count}, 删除 {removed_count})"
    )
    
    return corrected_detections, stats

