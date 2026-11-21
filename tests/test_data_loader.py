import json
import pytest
from shapely.geometry import Polygon, MultiPolygon, mapping
from data_loader import ROOT, load_scenario, geographic_geometry, project_geometry, checked_raw
import scenario_io as sio


def test_real_join_and_quantities():
    sc = load_scenario(ROOT / 'data/updated_input/Achampet_India_fleet1.geojson')
    assert len(sc.drones) == 5
    assert len({d['drone_id'] for d in sc.drones}) == 5
    assert len({d['model'] for d in sc.drones}) < 5
    assert sc.requirements[-1][0] == 'NOT_ASSIGNED'
    assert abs(sum(a for _, a in sc.requirements) - sc.domain.area) < 1e-6
    assert sc.audit['acd_minus_surface_m2'] != 0
    assert sc.audit['surface_csv_geojson_max_delta_m2'] == 0


def test_pdan_uses_paired_hull_and_source_requirements():
    sc = load_scenario(ROOT / 'data/updated_input/Achampet_India_fleet1.geojson', 'pdan')
    assert '_convex_hull_' in sc.path.name
    assert sc.audit['extra_area_m2'] > 0
    assert sc.domain.symmetric_difference(sc.original.convex_hull).area < 1e-5


def test_projection_roundtrip_holes_and_multipolygon():
    p = MultiPolygon([Polygon([(80, 16), (80.01, 16), (80.01, 16.01), (80, 16.01)],
                             [[(80.002, 16.002), (80.002, 16.003), (80.003, 16.003), (80.003, 16.002)]]),
                      Polygon([(80.02, 16), (80.03, 16), (80.03, 16.01), (80.02, 16.01)])])
    geom = mapping(p)
    origin = sio.origin_of(geom)
    projected = project_geometry(geom, origin)
    outers, holes = sio.rings(geom)
    sc = dict(outers=[sio.project(r, *origin) for r in outers], holes=[sio.project(r, *origin) for r in holes])
    assert sio.to_shapely(sc).symmetric_difference(projected).area < 1e-6
    assert geographic_geometry(projected, origin).symmetric_difference(p).area < 1e-15


def test_unknown_feature_rejected(tmp_path):
    fc = json.loads((ROOT / 'data/updated_input/Achampet_India_fleet1.geojson').read_text())
    fc['features'].append(dict(type='Feature', properties={'type': 'NoFlyZone'}, geometry=fc['features'][0]['geometry']))
    path = tmp_path / 'unknown.geojson'
    path.write_text(json.dumps(fc))
    with pytest.raises(ValueError, match='Schema'):
        checked_raw(path)
