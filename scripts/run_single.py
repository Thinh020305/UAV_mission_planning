from _cli import parser, execute

if __name__ == '__main__':
    p = parser('Phân vùng một kịch bản UAV')
    args = p.parse_args()
    if not args.scenario or args.algorithm == 'all' or args.strategy == 'all':
        p.error('Cần --scenario, một --algorithm và một --strategy')
    raise SystemExit(execute(args, [args.scenario]))
