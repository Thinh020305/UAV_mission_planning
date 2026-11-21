"""Mô phỏng Section 3.2: ba thuật toán và Balanced Strategy."""
from _cli import ROOT, parser, execute

if __name__ == '__main__':
    p = parser('Mô phỏng PODE, NPD, PDAN với Balanced Strategy')
    p.set_defaults(algorithm='all', strategy='balanced', output=ROOT / 'outputs/simulation')
    args = p.parse_args()
    path = args.scenario or ROOT / 'data/updated_input/Achampet_India_fleet1.geojson'
    raise SystemExit(execute(args, [path]))
