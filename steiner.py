import sys
import json
import time
import argparse
import heapq
from itertools import product

class Point:
    def __init__(self, x, y, id_, type_):
        self.x = x
        self.y = y
        self.id = id_
        self.type = type_

def manhattan(p1, p2):
    return abs(p1.x - p2.x) + abs(p1.y - p2.y)

def compute_mst(points):
    """Алгоритм Прима с кучей. Возвращает список рёбер и суммарную длину."""
    n = len(points)
    if n <= 1:
        return [], 0
    
    visited = [False] * n
    min_dist = [float('inf')] * n
    min_dist[0] = 0
    parent = [-1] * n
    total = 0
    pq = [(0, 0)]  # (расстояние, индекс вершины)

    while pq:
        dist, u = heapq.heappop(pq)
        if visited[u]:
            continue
        visited[u] = True
        total += dist
        
        for v in range(n):
            if not visited[v]:
                d = manhattan(points[u], points[v])
                if d < min_dist[v]:
                    min_dist[v] = d
                    parent[v] = u
                    heapq.heappush(pq, (d, v))
    
    edges = []
    for v in range(1, n):
        u = parent[v]
        if u != -1:
            edges.append((points[u].id, points[v].id))
    
    return edges, total

def generate_hanan_candidates(terminals, edge_bboxes=None):
    """
    Генерирует точки сетки Ханнана (x из X терминалов, y из Y терминалов).
    Если переданы edge_bboxes, кандидаты фильтруются по прямоугольникам рёбер.
    """
    xs = sorted({p.x for p in terminals})
    ys = sorted({p.y for p in terminals})
    term_coords = {(p.x, p.y) for p in terminals}
    candidates = []

    for x, y in product(xs, ys):
        if (x, y) in term_coords:
            continue
        
        # Если заданы edge_bboxes – точка должна попадать хотя бы в один прямоугольник
        if edge_bboxes:
            inside = False
            for (ex1, ex2, ey1, ey2) in edge_bboxes:
                if ex1 <= x <= ex2 and ey1 <= y <= ey2:
                    inside = True
                    break
            if inside:
                candidates.append(Point(x, y, -1, 's'))
        else:
            candidates.append(Point(x, y, -1, 's'))
    
    return candidates

def remove_degree_lt3_steiners(points, edges):
    """Удаляет точки Штейнера со степенью <3 и перестраивает связи."""
    adj = {p.id: [] for p in points}
    id_to_point = {p.id: p for p in points}
    
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)

    changed = True
    while changed:
        changed = False
        to_remove = [p for p in points if p.type == 's' and len(adj[p.id]) < 3]
        if not to_remove:
            break
        
        for p in to_remove:
            neighbors = adj[p.id]
            for nb in neighbors:
                adj[nb].remove(p.id)
            del adj[p.id]
            
            if len(neighbors) == 2:
                n1, n2 = neighbors[0], neighbors[1]
                adj[n1].append(n2)
                adj[n2].append(n1)
            
            points.remove(p)
            del id_to_point[p.id]
        changed = True

    new_edges = set()
    for u_id, lst in adj.items():
        for v_id in lst:
            if u_id < v_id:
                new_edges.add((u_id, v_id))
    
    return points, list(new_edges)

class SteinerSolver:
    def __init__(self, terminals):
        self.terminals = list(terminals)
        self.max_id = max((p.id for p in terminals), default=0)
        self.next_id = self.max_id + 1

    def _new_id(self):
        nid = self.next_id
        self.next_id += 1
        return nid

    def _initial_mst_length(self):
        _, length = compute_mst(self.terminals)
        return length

    def _get_edge_bboxes(self, points, edges):
        """Возвращает список ограничивающих прямоугольников для каждого ребра."""
        id_to_point = {p.id: p for p in points}
        bboxes = []
        for u_id, v_id in edges:
            pu = id_to_point[u_id]
            pv = id_to_point[v_id]
            x1, x2 = min(pu.x, pv.x), max(pu.x, pv.x)
            y1, y2 = min(pu.y, pv.y), max(pu.y, pv.y)
            bboxes.append((x1, x2, y1, y2))
        return bboxes

    def solve_basic(self):
        """Базовый алгоритм: перебор всех кандидатов Ханнана."""
        start = time.time()
        initial_len = self._initial_mst_length()
        points = list(self.terminals)
        all_candidates = generate_hanan_candidates(self.terminals)

        while True:
            cur_edges, cur_len = compute_mst(points)
            best_cand = None
            best_len = cur_len

            for cand in all_candidates:
                if any(p.x == cand.x and p.y == cand.y for p in points):
                    continue
                temp_points = points + [cand]
                _, temp_len = compute_mst(temp_points)
                if temp_len < best_len:
                    best_len = temp_len
                    best_cand = cand

            if best_cand is None:
                break
            
            new_pt = Point(best_cand.x, best_cand.y, self._new_id(), 's')
            points.append(new_pt)

        edges, _ = compute_mst(points)
        points, edges = remove_degree_lt3_steiners(points, edges)
        points_by_id = {p.id: p for p in points}
        final_len = sum(manhattan(points_by_id[u], points_by_id[v]) for u, v in edges)
        elapsed = time.time() - start
        steiner_added = sum(1 for p in points if p.type == 's')
        
        return points, edges, initial_len, final_len, elapsed, steiner_added

    def solve_modified(self):
        """
        Модифицированный алгоритм: кандидаты только в прямоугольниках,
        образованных текущими рёбрами MST.
        """
        start = time.time()
        initial_len = self._initial_mst_length()
        points = list(self.terminals)

        while True:
            cur_edges, cur_len = compute_mst(points)
            edge_bboxes = self._get_edge_bboxes(points, cur_edges)
            candidates = generate_hanan_candidates(self.terminals, edge_bboxes=edge_bboxes)
            best_cand = None
            best_len = cur_len

            for cand in candidates:
                if any(p.x == cand.x and p.y == cand.y for p in points):
                    continue
                temp_points = points + [cand]
                _, temp_len = compute_mst(temp_points)
                if temp_len < best_len:
                    best_len = temp_len
                    best_cand = cand

            if best_cand is None:
                break
            
            new_pt = Point(best_cand.x, best_cand.y, self._new_id(), 's')
            points.append(new_pt)

        edges, _ = compute_mst(points)
        points, edges = remove_degree_lt3_steiners(points, edges)
        points_by_id = {p.id: p for p in points}
        final_len = sum(manhattan(points_by_id[u], points_by_id[v]) for u, v in edges)
        elapsed = time.time() - start
        steiner_added = sum(1 for p in points if p.type == 's')
        
        return points, edges, initial_len, final_len, elapsed, steiner_added

def save_output(filename, points, edges):
    """Сохраняет результат в JSON."""
    output = {
        "node": [{"x": p.x, "y": p.y, "id": p.id, "type": p.type} for p in points],
        "edge": [{"nodes": [u, v]} for u, v in edges]
    }
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

def plot_tree(points, edges, title="Steiner Tree", save_path=None):
    """Визуализирует дерево и сохраняет в файл."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib not installed. Cannot visualize.")
        return
    
    plt.figure(figsize=(10, 8))
    id_to_point = {p.id: p for p in points}
    
    # Рёбра
    for u, v in edges:
        pu = id_to_point[u]
        pv = id_to_point[v]
        plt.plot([pu.x, pv.x], [pu.y, pv.y], 'b-', alpha=0.7, linewidth=2)
    
    # Терминалы
    term_x = [p.x for p in points if p.type == 't']
    term_y = [p.y for p in points if p.type == 't']
    plt.scatter(term_x, term_y, c='red', marker='o', s=100, label='Terminals', zorder=5)
    
    # Точки Штейнера
    stein_x = [p.x for p in points if p.type == 's']
    stein_y = [p.y for p in points if p.type == 's']
    if stein_x:
        plt.scatter(stein_x, stein_y, c='green', marker='s', s=80, label='Steiner points', zorder=5)
    
    # Подписи
    for p in points:
        plt.annotate(str(p.id), (p.x, p.y), textcoords="offset points",
                     xytext=(5, 5), ha='center', fontsize=8, 
                     bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis('equal')
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Visualization saved to {save_path}")
    else:
        plt.show()
    plt.close()

def main():
    parser = argparse.ArgumentParser(description='Steiner Tree Solver (L1 Manhattan)')
    parser.add_argument('input_file', help='Input JSON file')
    parser.add_argument('-m', '--modified', action='store_true', 
                        help='Use modified algorithm')
    parser.add_argument('-v', '--visualize', action='store_true', 
                        help='Visualize result and save to PNG file')
    args = parser.parse_args()

    # Чтение входного файла
    with open(args.input_file, 'r') as f:
        data = json.load(f)

    terminals = []
    for node in data['node']:
        if node.get('type') == 't':
            terminals.append(Point(node['x'], node['y'], node['id'], 't'))

    if not terminals:
        print("Error: No terminal points found in input file")
        return

    solver = SteinerSolver(terminals)

    # Выбор алгоритма
    if args.modified:
        points, edges, init_len, final_len, elapsed, steiner_cnt = solver.solve_modified()
        mode = "modified"
    else:
        points, edges, init_len, final_len, elapsed, steiner_cnt = solver.solve_basic()
        mode = "basic"

    # Вывод результатов
    print(f"\n{'='*50}")
    print(f"Algorithm: {mode}")
    print(f"Initial MST length: {init_len}")
    print(f"Final Steiner tree length: {final_len}")
    if init_len > 0:
        improvement = init_len - final_len
        percent = (improvement / init_len) * 100
        print(f"Improvement: {improvement} ({percent:.1f}%)")
    print(f"Time: {elapsed:.4f} s")
    print(f"Points: {len(points)} (Terminals: {len(terminals)}, Steiner: {steiner_cnt})")
    print(f"Edges: {len(edges)}")
    print(f"{'='*50}\n")

    # Сохранение результата
    out_name = args.input_file.rsplit('.', 1)[0] + '_out.json'
    save_output(out_name, points, edges)
    print(f"Saved to {out_name}")

    # Визуализация
    if args.visualize:
        img_name = args.input_file.rsplit('.', 1)[0] + '_out.png'
        plot_tree(points, edges, f"Steiner Tree ({mode}) Length={final_len}", save_path=img_name)

if __name__ == '__main__':
    main()