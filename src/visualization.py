"""Hình phân vùng và cây đệ quy phục vụ kiểm tra kết quả."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Patch
from matplotlib.path import Path
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient


def draw_geometry(ax, geometry, **kwargs):
    if geometry.is_empty:
        return
    for p in [geometry] if geometry.geom_type == 'Polygon' else geometry.geoms:
        p = orient(p, sign=1)
        vertices, codes = [], []
        for ring in [p.exterior, *p.interiors]:
            xy = list(ring.coords)
            vertices.extend(xy)
            codes.extend([Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY])
        ax.add_patch(PathPatch(Path(vertices, codes), **kwargs))


def plot_partition(sc, regions, title, path):
    fig, ax = plt.subplots(figsize=(10, 8), layout='constrained')
    handles = []
    for i, (key, geom) in enumerate(regions.items()):
        color = '#d8d8d8' if key == 'NOT_ASSIGNED' else plt.get_cmap('tab20')(i % 20)
        draw_geometry(ax, geom, facecolor=color, edgecolor='white', linewidth=1,
                      hatch='///' if key == 'NOT_ASSIGNED' else None, alpha=.85)
        if not geom.is_empty:
            p = geom.representative_point()
            ax.text(p.x, p.y, f'{key}\n{geom.area / 1e6:.3f} km²', fontsize=7, ha='center')
        handles.append(Patch(facecolor=color, label=key))
    extra = sc.domain.difference(sc.original)
    draw_geometry(ax, extra, facecolor='none', edgecolor='#b46b00', hatch='...', linewidth=.5)
    original_parts = [sc.original] if sc.original.geom_type == 'Polygon' else sc.original.geoms
    for polygon in original_parts:
        for ring in polygon.interiors:
            draw_geometry(ax, Polygon(ring), facecolor='#ed8888', edgecolor='#b02020', hatch='xx', alpha=.6)
    draw_geometry(ax, sc.original, facecolor='none', edgecolor='black', linewidth=1.4)
    handles.extend([Patch(facecolor='none', edgecolor='black', label='Biên vùng gốc'),
                    Patch(facecolor='#ed8888', hatch='xx', label='Lỗ / vùng cấm'),
                    Patch(facecolor='none', edgecolor='#b46b00', hatch='...', label='Mở rộng convex hull')])
    ax.legend(handles=handles, loc='upper left', bbox_to_anchor=(1, 1), fontsize=7)
    ax.autoscale_view()
    ax.set_aspect('equal')
    ax.set(xlabel='Đông (m)', ylabel='Bắc (m)', title=title)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_tree(trace, path):
    nodes = {row['node']: row for row in trace if 'node' in row}
    if not nodes:
        return
    leaves = sorted(k for k, v in nodes.items() if v['leaf'])
    xs = {k: i for i, k in enumerate(leaves)}
    for key in sorted(nodes, key=len, reverse=True):
        if key not in xs:
            xs[key] = (xs[key + 'L'] + xs[key + 'R']) / 2
    fig, ax = plt.subplots(figsize=(max(9, len(leaves) * 1.1), 6), layout='constrained')
    for key, row in nodes.items():
        depth = len(key) - 4
        if not row['leaf']:
            for child in (key + 'L', key + 'R'):
                ax.plot([xs[key], xs[child]], [-depth, -depth - 1], color='#8b9bad')
        label = ','.join(x.replace('UAV_', '') for x in row['ids'])
        ax.text(xs[key], -depth, f'{label}\n{row["area_m2"] / 1e6:.3f} km²',
                ha='center', va='center', fontsize=7,
                bbox=dict(boxstyle='round,pad=.4', facecolor='#d9eaff' if row['leaf'] else '#f4f4f4'))
    ax.set_title('Cây phân vùng (số là index UAV)')
    ax.axis('off')
    ax.margins(.1, .2)
    fig.savefig(path, dpi=150)
    plt.close(fig)
