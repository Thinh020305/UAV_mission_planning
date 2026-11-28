"""
Path Planning Module for Heterogeneous Multi-UAV Coverage (Step 3 / Person 3)
Based on: Zerrouk et al., "Increasing Automation on Mission Planning for
Heterogeneous Multi-Rotor Drone Fleets in Emergency Response", Drones 2025, 9, 816.
Section 3.3: Path Planning (Grid generation, sweep direction, A* obstacle avoidance).
"""

import math
import numpy as np
import networkx as nx
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, MultiLineString
from shapely.ops import unary_union
import matplotlib.pyplot as plt


def rotate_points(points, angle_rad):
    """Xoay mảng điểm (n, 2) theo góc angle_rad quanh gốc (0,0)."""
    pts = np.asarray(points, dtype=float)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    x = pts[:, 0] * cos_a - pts[:, 1] * sin_a
    y = pts[:, 0] * sin_a + pts[:, 1] * cos_a
    return np.column_stack([x, y])


def rotate_polygon(poly, angle_rad):
    """Xoay đối tượng shapely Polygon theo góc angle_rad."""
    ext = rotate_points(poly.exterior.coords, angle_rad)
    interiors = [rotate_points(r.coords, angle_rad) for r in poly.interiors]
    return Polygon(ext, holes=interiors)


def count_turns(waypoints, min_angle_deg=5.0):
    """
    Đếm số lần đổi hướng (rẽ) của đường bay.
    Rẽ được tính khi góc lệch hướng giữa 2 đoạn liên tiếp vượt min_angle_deg.
    """
    if len(waypoints) < 3:
        return 0
    w = np.asarray(waypoints, dtype=float)
    v1 = w[1:-1] - w[:-2]
    v2 = w[2:] - w[1:-1]
    
    norm1 = np.linalg.norm(v1, axis=1)
    norm2 = np.linalg.norm(v2, axis=1)
    valid = (norm1 > 1e-4) & (norm2 > 1e-4)
    if not np.any(valid):
        return 0
        
    dot = np.sum(v1[valid] * v2[valid], axis=1)
    cos_angle = np.clip(dot / (norm1[valid] * norm2[valid]), -1.0, 1.0)
    angles_deg = np.degrees(np.arccos(cos_angle))
    return int(np.sum(angles_deg > min_angle_deg))


def path_length(waypoints):
    """Tính tổng chiều dài đường bay (m) qua danh sách điểm."""
    if len(waypoints) < 2:
        return 0.0
    w = np.asarray(waypoints, dtype=float)
    diff = np.diff(w, axis=0)
    return float(np.sum(np.hypot(diff[:, 0], diff[:, 1])))


def build_visibility_graph(obstacles, extra_nodes=None):
    """
    Xây dựng Visibility Graph cho các chướng ngại vật (vùng cấm bay / lỗ).
    Các nút gồm đỉnh của chướng ngại vật và extra_nodes (ví dụ: điểm xuất phát, điểm đến).
    Cạnh nối 2 nút hợp lệ nếu đoạn thẳng nối chúng không cắt vào ruột chướng ngại vật.
    """
    nodes = []
    if extra_nodes:
        for p in extra_nodes:
            pt = (round(float(p[0]), 3), round(float(p[1]), 3))
            if pt not in nodes:
                nodes.append(pt)
                
    # Gom tất cả đỉnh của chướng ngại vật
    obs_union = unary_union(obstacles) if obstacles else None
    if obs_union and not obs_union.is_empty:
        if obs_union.geom_type == 'Polygon':
            obs_list = [obs_union]
        elif obs_union.geom_type == 'MultiPolygon':
            obs_list = list(obs_union.geoms)
        else:
            obs_list = []
            
        for ob in obs_list:
            for coord in list(ob.exterior.coords)[:-1]:
                pt = (round(float(coord[0]), 3), round(float(coord[1]), 3))
                if pt not in nodes:
                    nodes.append(pt)
            for hole in ob.interiors:
                for coord in list(hole.coords)[:-1]:
                    pt = (round(float(coord[0]), 3), round(float(coord[1]), 3))
                    if pt not in nodes:
                        nodes.append(pt)
                        
    G = nx.Graph()
    for n in nodes:
        G.add_node(n)
        
    # Tạo cạnh nối nếu không cắt vùng cấm
    num_nodes = len(nodes)
    for i in range(num_nodes):
        p1 = nodes[i]
        pt1 = Point(p1)
        for j in range(i + 1, num_nodes):
            p2 = nodes[j]
            line = LineString([p1, p2])
            is_valid = True
            if obs_union and not obs_union.is_empty:
                # Kiểm tra cắt vào phần ruột của chướng ngại vật (trừ biên bằng buffer âm nhỏ)
                safe_obs = obs_union.buffer(-1e-3)
                if not safe_obs.is_empty and line.intersects(safe_obs):
                    is_valid = False
            if is_valid:
                dist = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
                G.add_edge(p1, p2, weight=dist)
                
    return G, nodes


def find_avoidance_path(start, goal, obstacles):
    """
    Tìm đường đi ngắn nhất từ start đến goal tránh obstacles bằng A* trên Visibility Graph.
    """
    p_start = (round(float(start[0]), 3), round(float(start[1]), 3))
    p_goal = (round(float(goal[0]), 3), round(float(goal[1]), 3))
    
    # Kiểm tra đường bay thẳng trước để tăng tốc
    direct_line = LineString([p_start, p_goal])
    obs_union = unary_union(obstacles) if obstacles else None
    if not obs_union or obs_union.is_empty:
        return [list(p_start), list(p_goal)]
        
    safe_obs = obs_union.buffer(-1e-3)
    if safe_obs.is_empty or not direct_line.intersects(safe_obs):
        return [list(p_start), list(p_goal)]
        
    # Xây dựng Visibility Graph
    G, _ = build_visibility_graph(obstacles, extra_nodes=[p_start, p_goal])
    
    def heuristic(u, v):
        return math.hypot(u[0] - v[0], u[1] - v[1])
        
    try:
        path = nx.astar_path(G, p_start, p_goal, heuristic=heuristic, weight='weight')
        return [list(pt) for pt in path]
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        # Nếu không có đường (hoặc điểm rơi sát biên), fallback về đường thẳng
        return [list(p_start), list(p_goal)]


def generate_candidate_angles(polygon, n_discrete=3):
    """
    Tạo tập góc xoay ứng viên theo Mục 3.3.1 của bài báo:
    - Với mỗi cạnh của đa giác, tính góc căn chỉnh với trục X.
    - Cộng với N góc rời rạc {0, pi/N, ..., (N-1)pi/N}.
    """
    coords = list(polygon.exterior.coords)
    unique_angles = set()
    
    discrete_offsets = [k * math.pi / n_discrete for k in range(n_discrete)]
    
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        dx = x2 - x1
        dy = y2 - y1
        if math.hypot(dx, dy) < 1e-4:
            continue
        edge_angle = math.atan2(dy, dx)
        align_angle = -edge_angle  # góc xoay để cạnh song song với trục X
        
        for offset in discrete_offsets:
            angle = (align_angle + offset) % math.pi
            # Làm tròn đến 2 chữ số thập phân (độ) để loại bỏ góc trùng lặp
            deg = round(math.degrees(angle), 1) % 180.0
            unique_angles.add(round(math.radians(deg), 4))
            
    if not unique_angles:
        unique_angles.add(0.0)
    return sorted(list(unique_angles))


def generate_sweep_grid(rot_poly, sd, cd, hfp, vfp):
    """
    Tạo lưới các điểm quét (sweep lines và pass points) trên đa giác đã xoay.
    Theo Mục 3.3.1 bài báo:
    - Bắt đầu ở HFP/4 từ điểm đáy theo phương Y, khoảng cách giữa các dòng quét là SD.
    - Bắt đầu và kết thúc ở VFP/4 từ biên theo phương X, khoảng cách giữa các điểm là CD.
    """
    min_x, min_y, max_x, max_y = rot_poly.bounds
    
    y_start = min_y + hfp / 4.0
    if y_start > max_y:
        y_start = (min_y + max_y) / 2.0
        
    sweep_lines_points = []
    y = y_start
    
    while y <= max_y:
        # Tạo đường quét ngang cắt qua đa giác
        cut_line = LineString([(min_x - 100.0, y), (max_x + 100.0, y)])
        inter = cut_line.intersection(rot_poly)
        
        if not inter.is_empty:
            segments = []
            if inter.geom_type == 'LineString':
                segments = [inter]
            elif inter.geom_type == 'MultiLineString':
                segments = list(inter.geoms)
                
            line_pts = []
            for seg in segments:
                coords = list(seg.coords)
                x_left = min(coords[0][0], coords[-1][0])
                x_right = max(coords[0][0], coords[-1][0])
                
                # Trừ lề VFP/4 ở hai đầu
                x_start = x_left + vfp / 4.0
                x_end = x_right - vfp / 4.0
                
                if x_start <= x_end:
                    x_pts = []
                    curr_x = x_start
                    while curr_x <= x_end:
                        x_pts.append(curr_x)
                        curr_x += cd
                    if len(x_pts) == 0 or x_pts[-1] < x_end:
                        x_pts.append(x_end)
                    for px in x_pts:
                        pt = Point(px, y)
                        if rot_poly.buffer(1e-3).contains(pt):
                            line_pts.append([px, y])
            if line_pts:
                # Sắp xếp theo X tăng dần
                line_pts.sort(key=lambda p: p[0])
                sweep_lines_points.append(line_pts)
                
        y += sd
        
    return sweep_lines_points


def build_candidate_trajectory(sweep_lines, start_side='left'):
    """
    Nối các điểm quét thành đường ziczac (Mục 3.3.2).
    start_side: 'left' (vào từ đầu mút trái) hoặc 'right' (vào từ đầu mút phải của dòng quét đầu).
    """
    if not sweep_lines:
        return []
        
    trajectory = []
    ltr = (start_side == 'left')  # Left-to-Right flag
    
    for line in sweep_lines:
        pts = list(line)
        if not ltr:
            pts.reverse()
        trajectory.extend(pts)
        ltr = not ltr  # Đổi hướng quét ở dòng tiếp theo
        
    return trajectory


def plan_coverage_path(polygon, fleet_xy, sd, cd, hfp=None, vfp=None,
                       speed=10.0, mfd=20000.0, obstacles=None, n_rotations=3):
    """
    Hàm chính lập đường bay quét vùng cho 1 UAV (Người 3 bàn giao).
    
    Tham số:
    - polygon: đối tượng Shapely Polygon (đã ở hệ mét, có thể có lỗ).
    - fleet_xy: điểm xuất phát [x, y] (m).
    - sd: Sweep Distance (khoảng cách 2 làn quét, m).
    - cd: Capture Distance (khoảng cách 2 lần chụp, m).
    - hfp, vfp: Kích thước vết ảnh (m). Mặc định: hfp = 2*sd, vfp = 2*cd (overlap 50%).
    - speed: vận tốc UAV (m/s).
    - mfd: tầm bay tối đa (m).
    - obstacles: danh sách Polygon các vùng cấm bay / lỗ cần tránh.
    - n_rotations: số góc rời rạc N (mặc định 3 theo bài báo).
    
    Trả về dict:
    - 'waypoints': danh sách [x, y] từ trạm xuất phát -> quét -> về trạm
    - 'turns': số lần rẽ
    - 'distance_m': chiều dài đường bay (m)
    - 'flight_time_s': thời gian bay (s)
    - 'best_angle_deg': góc xoay tối ưu được chọn (độ)
    - 'exceeds_mfd': True nếu chiều dài bay vượt quá MFD
    - 'candidates_evaluated': tổng số đường bay ứng viên đã đánh giá
    """
    if hfp is None:
        hfp = 2.0 * sd
    if vfp is None:
        vfp = 2.0 * cd
        
    all_obstacles = list(obstacles) if obstacles else []
    # Thêm các lỗ của đa giác vào danh sách chướng ngại vật
    for hole in polygon.interiors:
        all_obstacles.append(Polygon(hole))
        
    candidate_angles = generate_candidate_angles(polygon, n_discrete=n_rotations)
    
    best_trajectory = None
    min_turns = float('inf')
    min_length = float('inf')
    best_angle = 0.0
    candidates_count = 0
    
    start_pt = list(fleet_xy)
    
    for angle in candidate_angles:
        rot_poly = rotate_polygon(polygon, angle)
        sweep_lines = generate_sweep_grid(rot_poly, sd, cd, hfp, vfp)
        
        if not sweep_lines:
            continue
            
        for side in ['left', 'right']:
            candidates_count += 1
            # 1. Tạo đường quét trong không gian xoay
            rot_scan = build_candidate_trajectory(sweep_lines, start_side=side)
            if not rot_scan:
                continue
                
            # 2. Xoay ngược lại hệ tọa độ ban đầu
            scan_waypoints = rotate_points(rot_scan, -angle).tolist()
            
            entry_pt = scan_waypoints[0]
            exit_pt = scan_waypoints[-1]
            
            # 3. Tránh vùng cấm từ start -> entry và từ exit -> start (Mục 3.3.3)
            path_in = find_avoidance_path(start_pt, entry_pt, all_obstacles)
            path_out = find_avoidance_path(exit_pt, start_pt, all_obstacles)
            
            # Ghép thành quỹ đạo hoàn chỉnh: start -> entry -> [scan] -> exit -> start
            full_path = path_in[:-1] + scan_waypoints + path_out[1:]
            
            # 4. Đánh giá số lần rẽ và chiều dài
            n_t = count_turns(full_path)
            length = path_length(full_path)
            
            # Quy tắc lựa chọn từ vựng: min Turns, sau đó min Distance (Công thức 8 và 9)
            if (n_t < min_turns) or (n_t == min_turns and length < min_length):
                min_turns = n_t
                min_length = length
                best_trajectory = full_path
                best_angle = math.degrees(angle)
                
    if best_trajectory is None:
        # Fallback nếu đa giác quá nhỏ không sinh được đường quét
        best_trajectory = [start_pt, list(polygon.centroid.coords)[0], start_pt]
        min_turns = 2
        min_length = path_length(best_trajectory)
        
    flight_time = min_length / max(speed, 0.1)
    
    return {
        'waypoints': best_trajectory,
        'turns': min_turns,
        'distance_m': round(min_length, 2),
        'flight_time_s': round(flight_time, 1),
        'best_angle_deg': round(best_angle, 1),
        'exceeds_mfd': min_length > mfd,
        'candidates_evaluated': candidates_count
    }


def plot_trajectory(polygon, result, fleet_xy, obstacles=None, title="Coverage Path Planning", save_path=None):
    """Vẽ minh họa đường bay quét và lưu ra file ảnh."""
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 1. Vẽ đa giác phân vùng
    x, y = polygon.exterior.xy
    ax.plot(x, y, color='green', linewidth=2, label='Phân vùng cần quét')
    ax.fill(x, y, color='green', alpha=0.1)
    
    # Vẽ các lỗ trong phân vùng
    for hole in polygon.interiors:
        hx, hy = hole.xy
        ax.plot(hx, hy, color='red', linewidth=1.5)
        ax.fill(hx, hy, color='red', alpha=0.3, label='Vùng cấm (Lỗ)' if 'Vùng cấm (Lỗ)' not in ax.get_legend_handles_labels()[1] else "")
        
    # 2. Vẽ vùng cấm ngoài nếu có
    if obstacles:
        for ob in obstacles:
            ox, oy = ob.exterior.xy
            ax.plot(ox, oy, color='red', linestyle='--', linewidth=1.5)
            ax.fill(ox, oy, color='red', alpha=0.25)
            
    # 3. Vẽ đường bay quét
    wps = np.asarray(result['waypoints'])
    ax.plot(wps[:, 0], wps[:, 1], color='blue', linewidth=1.5, alpha=0.8, label=f"Đường bay (Turns={result['turns']}, L={result['distance_m']}m)")
    ax.scatter(wps[1:-1, 0], wps[1:-1, 1], color='dodgerblue', s=15, zorder=4)
    
    # 4. Điểm cất cánh / hạ cánh
    ax.scatter([fleet_xy[0]], [fleet_xy[1]], color='darkorange', marker='^', s=120, zorder=5, label=f"Điểm xuất phát {fleet_xy}")
    
    ax.set_aspect('equal', 'box')
    ax.set_title(f"{title}\n(Quãng đường: {result['distance_m']}m, Số lần rẽ: {result['turns']}, Thời gian: {result['flight_time_s']}s)", fontsize=11)
    ax.set_xlabel("X (mét)")
    ax.set_ylabel("Y (mét)")
    ax.legend(loc='upper right')
    ax.grid(True, linestyle=':', alpha=0.6)
    
    if save_path:
        plt.savefig(save_path, dpi=200, bbox_inches='tight')
        plt.close()
    else:
        plt.show()
