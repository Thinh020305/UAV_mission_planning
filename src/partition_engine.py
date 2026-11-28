"""Pipeline dữ liệu thật -> partition -> kiểm chứng -> GeoJSON/metrics/figures."""
import json
from pathlib import Path
from time import perf_counter
import platform
from importlib.metadata import version
import pandas as pd
from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union
from data_loader import load_scenario, geographic_geometry, ROOT
from balanced_strategy import balanced_partition
from sequential_strategy import sequential_partition
from karmarkar_karp_strategy import karmarkar_karp_partition
from splitters import SPLITTERS
from metrics import region_metrics
from validation import validate_partition


def run_partition(path, algorithm='npd', strategy='balanced', *, data_folder=ROOT / 'data',
                  output=ROOT / 'outputs', steiner_points_count=25, figures=True):
    started = perf_counter()
    algorithm, strategy = algorithm.lower(), strategy.lower()
    if algorithm not in SPLITTERS or strategy not in ('balanced', 'sequential', 'karmarkar-karp'):
        raise ValueError('Cấu hình không được hỗ trợ')
    sc = load_scenario(path, algorithm, data_folder)
    splitter = SPLITTERS[algorithm](steiner_points_count) if algorithm == 'npd' else SPLITTERS[algorithm]()
    trace = []
    partition_started = perf_counter()
    partition = {
        'balanced': balanced_partition,
        'sequential': sequential_partition,
        'karmarkar-karp': karmarkar_karp_partition,
    }[strategy]
    regions = partition(sc.domain, sc.requirements, splitter, trace)
    partition_runtime = perf_counter() - partition_started
    validation = validate_partition(sc.domain, regions, dict(sc.requirements),
                                    sc.original.convex_hull.difference(sc.original)
                                    if sc.domain.equals(sc.original) else None)
    real = {k: g for k, g in regions.items() if k != 'NOT_ASSIGNED'}
    assigned = unary_union(list(real.values()))
    unassigned = regions.get('NOT_ASSIGNED', Polygon())
    drone_lookup = {d['drone_id']: d for d in sc.drones}
    rows = []
    for key, requested in sc.requirements:
        g = regions[key]
        rows.append(dict(drone_id=key, role='UNASSIGNED' if key == 'NOT_ASSIGNED' else 'UAV',
                         **region_metrics(g, requested),
                         original_intersection_m2=g.intersection(sc.original).area,
                         hull_extension_m2=g.difference(sc.original).area,
                         **{k: v for k, v in drone_lookup.get(key, {}).items() if k != 'drone_id'}))
    real_rows = [r for r in rows if r['role'] == 'UAV']
    report = dict(scenario=sc.name, computation_scenario=sc.path.name, algorithm=algorithm.upper(),
                  strategy=strategy.title(), fleet_size=len(real), assigned_area_m2=assigned.area,
                  unassigned_area_m2=unassigned.area,
                  coverage_percent=100 * assigned.intersection(sc.original).area / sc.original.area,
                  mean_area_error_m2=sum(r['area_error_m2'] for r in real_rows) / len(real_rows),
                  mean_compactness=sum(r['compactness'] for r in real_rows) / len(real_rows),
                  min_compactness=min(r['compactness'] for r in real_rows),
                  runtime_seconds=partition_runtime,
                  pipeline_seconds_before_export=perf_counter() - started,
                  status='OK_SOURCE_BACKED', extra_area_m2=sc.audit['extra_area_m2'],
                  original_area_m2=sc.original.area, domain_area_m2=sc.domain.area,
                  assigned_outside_original_m2=assigned.difference(sc.original).area,
                  unassigned_original_m2=unassigned.intersection(sc.original).area,
                  input_geometry='convex_hull' if '_convex_hull_' in sc.path.name else 'original',
                  steiner_points_count=steiner_points_count if algorithm == 'npd' else None,
                  experiment='extension' if algorithm == 'pode' and strategy == 'balanced' else 'reproduction_attempt',
                  reproduction='SOURCE_BACKED_NOT_PAPER_EXACT',
                  allocation_coverage_only=True, **{k: v for k, v in validation.items() if k != 'errors'})
    if strategy == 'balanced':
        report['greedy_tie_rule'] = 'largest_to_A_then_ties_to_B_stable_input_order'
    stem = f'{Path(sc.name).stem}__{algorithm}__{strategy}'
    output = Path(output)
    for sub in ('geojson', 'figures', 'metrics', 'traces'):
        (output / sub).mkdir(parents=True, exist_ok=True)
    features = []
    for row in rows:
        key = row['drone_id']
        props = dict(row, algorithm=algorithm.upper(), strategy=strategy.title(),
                     reproduction=report['reproduction'], input_geometry=report['input_geometry'])
        features.append(dict(type='Feature', properties=props,
                             geometry=mapping(geographic_geometry(regions[key], sc.origin))))
    # Lớp reference riêng, không được cộng vào hợp vùng phân công.
    context_features = [dict(type='Feature', properties={'role': 'ORIGINAL_BOUNDARY'},
                             geometry=mapping(geographic_geometry(sc.original, sc.origin))),
                        dict(type='Feature', properties={'role': 'HULL_EXTENSION'},
                             geometry=mapping(geographic_geometry(sc.domain.difference(sc.original), sc.origin)))]
    original_parts = [sc.original] if sc.original.geom_type == 'Polygon' else sc.original.geoms
    for part in original_parts:
        for ring in part.interiors:
            context_features.append(dict(type='Feature', properties={'role': 'NO_FLY_HOLE'},
                                         geometry=mapping(geographic_geometry(Polygon(ring), sc.origin))))
    fc = dict(type='FeatureCollection', features=features,
              metadata=dict(report=report, audit=sc.audit,
                            versions={p: version(p) for p in ('pode', 'npd', 'pdan', 'shapely')},
                            python=platform.python_version(),
                            hull_flight_safety_validated=False if algorithm == 'pdan' else None))
    (output / 'geojson' / f'{stem}.geojson').write_text(json.dumps(fc, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    (output / 'geojson' / f'{stem}__context.geojson').write_text(json.dumps(dict(type='FeatureCollection', features=context_features), ensure_ascii=False), encoding='utf-8')
    pd.DataFrame(rows).to_csv(output / 'metrics' / f'{stem}__regions.csv', index=False)
    pd.DataFrame([report]).to_csv(output / 'metrics' / f'{stem}.csv', index=False)
    (output / 'traces' / f'{stem}.json').write_text(json.dumps(trace, ensure_ascii=False), encoding='utf-8')
    if figures:
        from visualization import plot_partition, plot_tree
        plot_partition(sc, regions, f'{Path(sc.name).stem}\n{algorithm.upper()} / {strategy.title()}', output / 'figures' / f'{stem}.png')
        if strategy in ('balanced', 'karmarkar-karp'):
            plot_tree(trace, output / 'figures' / f'{stem}__tree.png')
    return report
