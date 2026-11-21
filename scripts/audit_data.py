"""Audit toàn bộ dữ liệu và lưu manifest SHA256, không sửa input."""
from pathlib import Path
import sys
import json
import hashlib
from collections import Counter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import scenario_io as sio
from data_loader import checked_raw, project_geometry


def audit():
    folder = ROOT / 'data'
    s = pd.read_csv(folder / 'scenarios_step1.csv')
    d = pd.read_csv(folder / 'drones_step1.csv')
    rows, features, models, prop_sets, hashes = [], Counter(), Counter(), Counter(), {}
    for path in sorted((folder / 'updated_input').glob('*.geojson')):
        fc, geom, drones = checked_raw(path)
        domain = project_geometry(geom, sio.origin_of(geom))
        polygons = [domain] if domain.geom_type == 'Polygon' else domain.geoms
        csv_s = s[s.scenario == path.name]
        csv_d = d[d.scenario == path.name].sort_values('idx')
        if len(csv_s) != 1 or list(csv_d.idx) != list(range(len(drones))):
            raise ValueError(f'Join sai: {path.name}')
        for f in fc['features']:
            features[f['properties']['type']] += 1
            prop_sets[','.join(sorted(f['properties']))] += 1
        models.update(f['properties']['model'] for f in drones)
        surface_diffs = [float(r.surface_updated_m2) - float(f['properties']['surface'])
                         for (_, r), f in zip(csv_d.iterrows(), drones)]
        rows.append(dict(scenario=path.name, convex_hull='_convex_hull_' in path.name,
                         geometry_type=geom['type'], valid=domain.is_valid,
                         holes=sum(len(p.interiors) for p in polygons),
                         vertices=sum(len(p.exterior.coords) - 1 for p in polygons),
                         fleet_size=len(drones), feature_count=len(fc['features']), area_m2=domain.area,
                         csv_area_delta_m2=float(csv_s.iloc[0].area_m2) - domain.area,
                         surface_csv_geojson_max_delta_m2=max(map(abs, surface_diffs)),
                         acd_minus_updated_m2=float(csv_d.acd_m2.sum() - csv_d.surface_updated_m2.sum()),
                         requirement_sum_m2=float(csv_d.requirement_m2.sum()),
                         csv_not_assigned_m2=float(csv_s.iloc[0].not_assigned_m2),
                         closure_delta_m2=float(csv_d.requirement_m2.sum() + csv_s.iloc[0].not_assigned_m2 - domain.area),
                         repeated_models=len(drones) - len(set(f['properties']['model'] for f in drones))))
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [folder / 'scenarios_step1.csv', folder / 'drones_step1.csv', ROOT / 'src/fleet_analysis.py', ROOT / 'src/scenario_io.py']:
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    out = ROOT / 'outputs/audit'
    out.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    table.to_csv(out / 'data_audit.csv', index=False)
    summary = dict(scenarios=len(rows), scenario_csv_rows=len(s), drone_csv_rows=len(d),
                   polygon_names=int(s.polygon.nunique()), scenario_headers=list(s.columns), drone_headers=list(d.columns),
                   geometry_types=dict(Counter(r['geometry_type'] for r in rows)),
                   feature_types=dict(features), properties=dict(prop_sets), models=dict(models),
                   invalid_scenarios=int((~table.valid).sum()),
                   hull_scenarios=int(table.convex_hull.sum()), original_scenarios=int((~table.convex_hull).sum()),
                   max_holes=int(table.holes.max()), fleet_sizes=sorted(table.fleet_size.unique().tolist()),
                   max_surface_csv_geojson_delta_m2=float(table.surface_csv_geojson_max_delta_m2.max()),
                   max_csv_area_delta_m2=float(table.csv_area_delta_m2.abs().max()),
                   max_closure_delta_m2=float(table.closure_delta_m2.abs().max()),
                   max_acd_surface_delta_m2=float(table.acd_minus_updated_m2.abs().max()),
                   duplicate_scenario_rows=int(s.scenario.duplicated().sum()),
                   duplicate_drone_keys=int(d.duplicated(['scenario', 'idx']).sum()))
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    (out / 'manifest_sha256.json').write_text(json.dumps(hashes, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    audit()
