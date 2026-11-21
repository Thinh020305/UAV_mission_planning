from _cli import parser, execute

if __name__ == '__main__':
    p = parser('So sánh sáu cấu hình trên cùng kịch bản')
    p.set_defaults(algorithm='all', strategy='all')
    args = p.parse_args()
    if not args.scenario:
        p.error('Cần --scenario')
    raise SystemExit(execute(args, [args.scenario]))
