import json
import pytest
from shapely.geometry import shape
from partition_engine import run_partition
from data_loader import ROOT, project_geometry


@pytest.mark.parametrize('algorithm', ['pode', 'npd', 'pdan'])
@pytest.mark.parametrize('strategy', ['sequential', 'balanced'])
def test_real_geojson_export(tmp_path, algorithm, strategy):
    path = ROOT / 'data/updated_input/Achampet_India_fleet1.geojson'
    report = run_partition(path, algorithm, strategy, output=tmp_path, figures=False)
    assert report['valid'] and report['status'] == 'OK_SOURCE_BACKED'
    output = tmp_path / 'geojson' / f'{path.stem}__{algorithm}__{strategy}.geojson'
    fc = json.loads(output.read_text(encoding='utf-8'))
    assert len(fc['features']) == 6
    assert sum(f['properties']['role'] == 'UAV' for f in fc['features']) == 5
    for feature in fc['features']:
        geometry = shape(feature['geometry'])
        assert geometry.is_valid
        assert -180 <= geometry.bounds[0] <= 180
        assert -90 <= geometry.bounds[1] <= 90
        planar = project_geometry(feature['geometry'], fc['metadata']['audit']['origin'])
        assert abs(planar.area - feature['properties']['actual_area_m2']) < .001
