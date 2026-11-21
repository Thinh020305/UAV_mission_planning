"""CLI dùng chung, chạy từ bất kỳ working directory nào."""
from pathlib import Path
import sys
import argparse
import traceback
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from partition_engine import run_partition


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument('--scenario', type=Path)
    p.add_argument('--input-folder', type=Path, default=ROOT / 'data/updated_input')
    p.add_argument('--data-folder', type=Path, default=ROOT / 'data')
    p.add_argument('--output', type=Path, default=ROOT / 'outputs')
    p.add_argument('--algorithm', choices=['all', 'pode', 'npd', 'pdan'], default='npd')
    p.add_argument('--strategy', choices=['all', 'sequential', 'balanced'], default='balanced')
    p.add_argument('--steiner-points', type=int, default=25)
    p.add_argument('--no-figures', action='store_true')
    p.add_argument('--limit', type=int)
    p.add_argument('--include-hull-inputs', action='store_true', help='Thêm 400 bản hull làm input độc lập; PDAN mặc định đã dùng hull tương ứng')
    return p


def execute(args, paths):
    rows = []
    algorithms = ['pode', 'npd', 'pdan'] if args.algorithm == 'all' else [args.algorithm]
    strategies = ['sequential', 'balanced'] if args.strategy == 'all' else [args.strategy]
    paths = list(paths)
    if args.limit is not None:
        paths = paths[:args.limit]
    args.output.mkdir(parents=True, exist_ok=True)
    failures = []
    for path in paths:
        for algorithm in algorithms:
            for strategy in strategies:
                try:
                    row = run_partition(path, algorithm, strategy, data_folder=args.data_folder,
                                        output=args.output, steiner_points_count=args.steiner_points,
                                        figures=not args.no_figures)
                    print(f'{path.name}: {algorithm}/{strategy} OK, {row["runtime_seconds"]:.3f}s', flush=True)
                except Exception as exc:
                    row = dict(scenario=path.name, algorithm=algorithm.upper(), strategy=strategy.title(),
                               status='FAILED', error=f'{type(exc).__name__}: {exc}')
                    failures.append(dict(row, traceback=traceback.format_exc()))
                    print(f'{path.name}: {algorithm}/{strategy} FAILED: {exc}', flush=True)
                rows.append(row)
                pd.DataFrame(rows).to_csv(args.output / 'comparison.csv', index=False)
                (args.output / 'failures.json').write_text(json.dumps(failures, ensure_ascii=False), encoding='utf-8')
    return int(bool(failures))
