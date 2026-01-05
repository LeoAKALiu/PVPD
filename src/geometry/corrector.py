"""几何校正模块 - 使用 RANSAC 回归和网格填充算法修正检测结果."""

import logging
from typing import Any, Optional

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
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


def detect_main_direction(points: np.ndarray) -> str:
    """
    检测点云的主要方向.
    
    Args:
        points: 点坐标数组，形状为 (n_points, 2)
        
    Returns:
        "horizontal" (主要沿 X 轴), "vertical" (主要沿 Y 轴), 或 "mixed"
    """
    if len(points) < 3:
        return "mixed"
    
    from sklearn.decomposition import PCA
    
    # 标准化点坐标（减去均值）
    points_centered = points - points.mean(axis=0)
    
    # PCA 分析
    pca = PCA(n_components=2)
    pca.fit(points_centered)
    
    # 主成分的方差比
    variance_ratio = pca.explained_variance_ratio_
    
    # 如果第一个主成分的方差占比 > 0.7，说明主要沿一个方向分布
    if variance_ratio[0] > 0.7:
        # 判断是横向还是纵向
        first_pc = pca.components_[0]
        if abs(first_pc[0]) > abs(first_pc[1]):
            return "horizontal"  # 主要沿 X 轴（横向）
        else:
            return "vertical"    # 主要沿 Y 轴（纵向）
    
    return "mixed"  # 混合方向


def fit_grid_with_ransac(
    points: np.ndarray,
    degree: int = 2,
    residual_threshold: float = 10.0,
    max_trials: int = 100,
    use_adaptive_direction: bool = True,
    max_correction_distance: float = 50.0,
) -> tuple[Any, np.ndarray]:
    """
    使用 RANSAC 回归拟合网格（改进版：自适应方向 + 限制校正距离）.
    
    Args:
        points: 点坐标数组，形状为 (n_points, 2)，每行为 (x, y)
        degree: 多项式次数（默认 2，表示二次拟合）
        residual_threshold: 残差阈值
        max_trials: 最大迭代次数
        use_adaptive_direction: 是否使用自适应方向检测
        max_correction_distance: 最大校正距离（像素），超过此距离的点不移动
        
    Returns:
        (拟合模型, 拟合后的点坐标)
    """
    if len(points) < 3:
        logger.warning("点数不足，无法进行 RANSAC 拟合")
        return None, points
    
    # 自适应方向检测
    direction = "horizontal"
    if use_adaptive_direction:
        direction = detect_main_direction(points)
        logger.debug(f"检测到主要方向: {direction}")
    
    # 根据方向选择拟合轴
    if direction == "vertical":
        # 垂直列：使用 x = f(y) 拟合
        x = points[:, 1].reshape(-1, 1)  # 使用 y 作为输入
        y = points[:, 0]                  # 使用 x 作为输出
        swap_axes = True
    else:
        # 水平列或混合：使用 y = f(x) 拟合
        x = points[:, 0].reshape(-1, 1)  # 使用 x 作为输入
        y = points[:, 1]                  # 使用 y 作为输出
        swap_axes = False
    
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
    
    # 预测拟合后的坐标
    y_pred = ransac.predict(x_poly)
    
    # 构建拟合后的点坐标
    if swap_axes:
        fitted_points = np.column_stack([y_pred, x.flatten()])
    else:
        fitted_points = np.column_stack([x.flatten(), y_pred])
    
    # 改进策略：不强制移动所有点，只对明显偏离的点进行校正
    # 计算原始点到拟合点的距离
    from scipy.spatial.distance import cdist
    distances = np.linalg.norm(points - fitted_points, axis=1)
    
    # 对于距离超过 max_correction_distance 的点，保持原始位置
    # 这些点可能是误检或不在拟合模型中的点
    correction_mask = distances <= max_correction_distance
    
    if np.sum(correction_mask) < len(points) * 0.5:
        # 如果超过一半的点都需要大幅移动，说明拟合模型可能不准确
        logger.warning(
            f"拟合模型可能不准确：只有 {np.sum(correction_mask)}/{len(points)} "
            f"个点在合理范围内，保持原始点位置"
        )
        return ransac, points
    
    # 只校正距离合理的点
    corrected_points = points.copy()
    corrected_points[correction_mask] = fitted_points[correction_mask]
    
    logger.debug(
        f"RANSAC 拟合完成：校正 {np.sum(correction_mask)}/{len(points)} 个点，"
        f"平均偏移: {distances[correction_mask].mean():.1f}px"
    )
    
    return ransac, corrected_points


def fill_grid(
    points: np.ndarray,
    image_shape: tuple[int, int],
    grid_spacing: float = 50.0,
) -> np.ndarray:
    """
    使用网格填充算法生成缺失的检测点.
    
    只在检测到的点附近填充缺失的点，而不是在整个图像上生成网格。
    
    Args:
        points: 现有点坐标数组，形状为 (n_points, 2)
        image_shape: 图像尺寸 (height, width)
        grid_spacing: 网格间距（像素）
        
    Returns:
        填充后的点坐标数组
    """
    height, width = image_shape
    
    # 如果没有现有点，返回空数组（不应该填充整个图像）
    if len(points) == 0:
        logger.warning("没有现有点，跳过网格填充")
        return points
    
    # 计算现有点的边界框（带扩展）
    # 扩展范围：在边界框周围扩展 1 倍 grid_spacing（更保守）
    margin = grid_spacing
    x_min = max(0, float(np.min(points[:, 0])) - margin)
    x_max = min(width, float(np.max(points[:, 0])) + margin)
    y_min = max(0, float(np.min(points[:, 1])) - margin)
    y_max = min(height, float(np.max(points[:, 1])) + margin)
    
    # 只在边界框内创建网格
    x_grid = np.arange(x_min, x_max, grid_spacing)
    y_grid = np.arange(y_min, y_max, grid_spacing)
    
    if len(x_grid) == 0 or len(y_grid) == 0:
        logger.warning("边界框太小，无法生成网格")
        return points
    
    # 生成网格点
    xx, yy = np.meshgrid(x_grid, y_grid)
    grid_points = np.column_stack([xx.ravel(), yy.ravel()])
    
    # 计算每个网格点到最近现有点的距离
    from scipy.spatial.distance import cdist
    
    distances = cdist(grid_points, points)
    min_distances = np.min(distances, axis=1)
    
    # 只保留距离现有点在合理范围内的点（可能是缺失的检测）
    # 同时排除距离太近的点（避免重复）
    min_threshold = grid_spacing * 0.5  # 最小距离，避免重复（更保守）
    max_threshold = grid_spacing * 0.9  # 最大距离，只在很近的范围内填充（更保守）
    
    new_points_mask = (min_distances >= min_threshold) & (min_distances <= max_threshold)
    
    # 添加新点
    new_points = grid_points[new_points_mask]
    
    if len(new_points) > 0:
        # 合并现有点和新点
        all_points = np.vstack([points, new_points])
        logger.debug(f"网格填充: 原始 {len(points)} 个点，新增 {len(new_points)} 个点")
    else:
        all_points = points
    
    return all_points


def find_chains(
    points: np.ndarray,
    search_radius: float,
    angle_threshold: float = 15.0,
    min_chain_length: int = 3,
) -> list[list[int]]:
    """
    使用链式搜索算法识别桩列（链）.
    
    Args:
        points: 点坐标数组，形状为 (n_points, 2)
        search_radius: 搜索半径（像素）
        angle_threshold: 角度阈值（度），向量夹角超过此值则断开连接
        min_chain_length: 最小链长度，长度小于此值的链将被过滤
        
    Returns:
        链列表，每个链是点的索引列表
    """
    if len(points) < 2:
        return []
    
    n_points = len(points)
    
    # 构建 KD-Tree 用于快速最近邻搜索
    tree = cKDTree(points)
    
    # 构建邻接图
    edges: dict[int, list[int]] = {i: [] for i in range(n_points)}
    
    for i in range(n_points):
        # 搜索半径内的所有点
        neighbors = tree.query_ball_point(points[i], search_radius)
        neighbors.remove(i)  # 移除自己
        
        for j in neighbors:
            # 计算方向向量
            vec_ij = points[j] - points[i]
            dist_ij = np.linalg.norm(vec_ij)
            
            if dist_ij > 0:
                # 归一化方向向量
                vec_ij_norm = vec_ij / dist_ij
                
                # 检查方向是否主要沿 Y 轴（垂直列）或 X 轴（水平列）
                # 对于垂直列，主要看 y 分量；对于水平列，主要看 x 分量
                # 降低阈值，使其更宽松（从 0.7 改为 0.5）
                if abs(vec_ij_norm[1]) > abs(vec_ij_norm[0]):
                    # 垂直方向为主
                    if abs(vec_ij_norm[1]) > 0.5:  # 方向一致性阈值（降低阈值）
                        edges[i].append(j)
                else:
                    # 水平方向为主
                    if abs(vec_ij_norm[0]) > 0.5:  # 方向一致性阈值（降低阈值）
                        edges[i].append(j)
    
    # 使用深度优先搜索找到所有链
    visited = set()
    chains: list[list[int]] = []
    
    def dfs_chain(current: int, chain: list[int]) -> None:
        """深度优先搜索构建链."""
        visited.add(current)
        chain.append(current)
        
        # 检查角度一致性
        if len(chain) >= 2:
            # 计算前两个点的向量
            vec1 = points[chain[-1]] - points[chain[-2]]
            vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-8)
            
            # 检查所有可能的下一跳
            for neighbor in edges[current]:
                if neighbor not in visited:
                    # 计算当前点到邻居的向量
                    vec2 = points[neighbor] - points[current]
                    vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-8)
                    
                    # 计算夹角（使用点积）
                    dot_product = np.clip(np.dot(vec1_norm, vec2_norm), -1.0, 1.0)
                    angle = np.arccos(dot_product) * 180.0 / np.pi
                    
                    # 如果角度小于阈值，继续搜索
                    if angle <= angle_threshold:
                        dfs_chain(neighbor, chain)
                        return
        
        # 如果没有满足角度要求的下一跳，尝试所有未访问的邻居
        for neighbor in edges[current]:
            if neighbor not in visited:
                dfs_chain(neighbor, chain)
                return
    
    # 从每个未访问的点开始搜索
    for i in range(n_points):
        if i not in visited:
            chain: list[int] = []
            dfs_chain(i, chain)
            if len(chain) >= min_chain_length:
                chains.append(chain)
    
    logger.info(f"链式搜索完成：找到 {len(chains)} 条链（最小长度: {min_chain_length}）")
    
    return chains


def complete_chains(
    points: np.ndarray,
    chains: list[list[int]],
    median_spacing: float,
    max_gap_ratio: float = 2.5,
) -> tuple[np.ndarray, int]:
    """
    补全链中缺失的点.
    
    Args:
        points: 点坐标数组，形状为 (n_points, 2)
        chains: 链列表，每个链是点的索引列表
        median_spacing: 基准间距（像素）
        max_gap_ratio: 最大间隙比例，超过此比例的间隙不补全
        
    Returns:
        (补全后的点坐标数组, 新增点数)
    """
    if len(chains) == 0:
        return points, 0
    
    new_points: list[np.ndarray] = [points.copy()]
    added_count = 0
    
    for chain in chains:
        if len(chain) < 2:
            continue
        
        # 按链的顺序处理点
        chain_points = points[chain]
        
        for i in range(len(chain) - 1):
            p1 = chain_points[i]
            p2 = chain_points[i + 1]
            
            # 计算两点之间的距离
            dist = np.linalg.norm(p2 - p1)
            
            # 计算期望的点数（包括起点和终点）
            expected_count = int(np.round(dist / median_spacing)) + 1
            
            # 如果距离是标准间距的整数倍（在容差范围内），补全缺失的点
            if expected_count > 2:  # 至少需要补一个点
                gap_ratio = dist / median_spacing
                if gap_ratio <= max_gap_ratio:
                    # 计算需要插入的点数
                    insert_count = expected_count - 2  # 减去起点和终点
                    
                    # 在两点之间插值
                    for j in range(1, insert_count + 1):
                        t = j / (insert_count + 1)
                        new_point = p1 + t * (p2 - p1)
                        new_points.append(new_point.reshape(1, -1))
                        added_count += 1
    
    if added_count > 0:
        all_points = np.vstack(new_points)
        logger.info(f"链补全完成：新增 {added_count} 个点")
        return all_points, added_count
    
    return points, 0


def apply_chain_based_correction(
    detections: list[Detection],
    image_shape: tuple[int, int],
    search_radius: Optional[float] = None,
    angle_threshold: float = 15.0,
    min_chain_length: int = 3,
    max_gap_ratio: float = 2.5,
) -> tuple[list[Detection], dict[str, Any]]:
    """
    使用链式搜索算法进行几何校正.
    
    Args:
        detections: 原始检测结果列表
        image_shape: 图像尺寸 (height, width)
        search_radius: 搜索半径（像素），如果为 None 则自动计算
        angle_threshold: 角度阈值（度）
        min_chain_length: 最小链长度
        max_gap_ratio: 最大间隙比例
        
    Returns:
        (校正后的检测结果列表, 统计信息字典)
    """
    if not detections:
        logger.warning("检测结果为空，跳过链式搜索校正")
        return [], {
            "original_count": 0,
            "corrected_count": 0,
            "added_count": 0,
            "removed_count": 0,
        }
    
    original_count = len(detections)
    logger.info(f"开始链式搜索几何校正，原始检测数: {original_count}")
    
    # 提取中心点坐标
    points = np.array([[det.x_center, det.y_center] for det in detections])
    
    # 计算基准间距（用于搜索半径和补全）
    distances = cdist(points, points)
    distances[distances == 0] = np.inf
    min_distances = np.min(distances, axis=1)
    median_spacing = float(np.median(min_distances))
    
    # 如果未指定搜索半径，使用基准间距的 2.0 倍（增加搜索半径）
    if search_radius is None:
        search_radius = median_spacing * 2.0
        logger.debug(f"自动计算搜索半径: {search_radius:.1f}px（基准间距: {median_spacing:.1f}px）")
    
    # 步骤 1: 找到所有链
    chains = find_chains(
        points,
        search_radius=search_radius,
        angle_threshold=angle_threshold,
        min_chain_length=min_chain_length,
    )
    
    if len(chains) == 0:
        logger.warning("未找到任何链，保持原始检测结果")
        return detections, {
            "original_count": original_count,
            "corrected_count": original_count,
            "added_count": 0,
            "removed_count": 0,
        }
    
    # 收集所有在链中的点索引
    chain_indices = set()
    for chain in chains:
        chain_indices.update(chain)
    
    # 步骤 2: 过滤掉不在任何链中的点（可能是误检）
    filtered_points = points[list(chain_indices)]
    filtered_detections = [detections[i] for i in chain_indices]
    removed_count = original_count - len(filtered_points)
    
    logger.info(f"过滤完成：保留 {len(filtered_points)} 个点，移除 {removed_count} 个孤立点")
    
    # 步骤 3: 补全链中缺失的点
    # 需要重建链索引（因为过滤后索引改变了）
    # 为了简化，我们使用过滤后的点重新构建链
    if len(filtered_points) >= 2:
        # 重新构建 KD-Tree 和链（使用过滤后的点）
        filtered_chains = find_chains(
            filtered_points,
            search_radius=search_radius,
            angle_threshold=angle_threshold,
            min_chain_length=min_chain_length,
        )
        
        completed_points, added_count = complete_chains(
            filtered_points,
            filtered_chains,
            median_spacing=median_spacing,
            max_gap_ratio=max_gap_ratio,
        )
    else:
        completed_points = filtered_points
        added_count = 0
    
    # 构建校正后的检测结果
    corrected_detections: list[Detection] = []
    
    # 首先添加原始过滤后的检测（保持置信度等信息）
    for det in filtered_detections:
        corrected_detections.append(det)
    
    # 然后添加补全的点（使用默认值）
    if added_count > 0:
        new_point_start_idx = len(filtered_points)
        for i in range(added_count):
            point = completed_points[new_point_start_idx + i]
            x_center, y_center = point[0], point[1]
            default_width = 50.0
            default_height = 50.0
            x = x_center - default_width / 2.0
            y = y_center - default_height / 2.0
            
            corrected_det = Detection(
                bbox=[x, y, default_width, default_height],
                confidence=0.5,  # 默认置信度
                category_id=0,
            )
            corrected_detections.append(corrected_det)
    
    corrected_count = len(corrected_detections)
    
    stats = {
        "original_count": original_count,
        "corrected_count": corrected_count,
        "added_count": added_count,
        "removed_count": removed_count,
    }
    
    logger.info(
        f"链式搜索几何校正完成: 原始 {original_count} -> 校正后 {corrected_count} "
        f"(新增 {added_count}, 删除 {removed_count})"
    )
    
    return corrected_detections, stats


def apply_geometric_correction(
    detections: list[Detection],
    image_shape: tuple[int, int],
    use_chain_search: bool = False,
    use_ransac: bool = True,
    use_grid_fill: bool = True,
    ransac_degree: int = 2,
    ransac_threshold: float = 10.0,
    grid_spacing: float = 50.0,
    chain_search_radius: Optional[float] = None,
    chain_angle_threshold: float = 20.0,
    chain_min_length: int = 3,
    chain_max_gap_ratio: float = 2.5,
) -> tuple[list[Detection], dict[str, Any]]:
    """
    应用几何校正到检测结果.
    
    Args:
        detections: 原始检测结果列表
        image_shape: 图像尺寸 (height, width)
        use_chain_search: 是否使用链式搜索算法（推荐）
        use_ransac: 是否使用 RANSAC 回归（仅在 use_chain_search=False 时有效）
        use_grid_fill: 是否使用网格填充（仅在 use_chain_search=False 时有效）
        ransac_degree: RANSAC 多项式次数
        ransac_threshold: RANSAC 残差阈值
        grid_spacing: 网格填充间距
        chain_search_radius: 链式搜索半径（像素），如果为 None 则自动计算
        chain_angle_threshold: 链式搜索角度阈值（度）
        chain_min_length: 链式搜索最小链长度
        chain_max_gap_ratio: 链式搜索最大间隙比例
        
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
    
    # 如果使用链式搜索，直接调用链式搜索函数
    if use_chain_search:
        return apply_chain_based_correction(
            detections,
            image_shape,
            search_radius=chain_search_radius,
            angle_threshold=chain_angle_threshold,
            min_chain_length=chain_min_length,
            max_gap_ratio=chain_max_gap_ratio,
        )
    
    original_count = len(detections)
    logger.info(f"开始几何校正，原始检测数: {original_count}")
    
    # 提取中心点坐标
    points = np.array([[det.x_center, det.y_center] for det in detections])
    
    corrected_points = points.copy()
    
    # RANSAC 回归校正
    if use_ransac and len(points) >= 3:
        try:
            # 计算基准间距，用于限制校正距离
            from scipy.spatial.distance import cdist
            distances = cdist(points, points)
            distances[distances == 0] = np.inf
            min_distances = np.min(distances, axis=1)
            median_spacing = float(np.median(min_distances))
            
            # 最大校正距离设为基准间距的一半（更保守）
            max_correction_distance = max(median_spacing * 0.5, 30.0)
            
            ransac_model, fitted_points = fit_grid_with_ransac(
                points,
                degree=ransac_degree,
                residual_threshold=ransac_threshold,
                use_adaptive_direction=True,
                max_correction_distance=max_correction_distance,
            )
            
            if ransac_model is not None:
                corrected_points = fitted_points
                logger.info(
                    f"RANSAC 回归完成（自适应方向，最大校正距离: {max_correction_distance:.1f}px）"
                )
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

