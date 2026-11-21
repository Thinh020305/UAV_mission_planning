from _cli import parser, execute

if __name__ == '__main__':
    p = parser('Chạy tập dữ liệu với kết quả từng cấu hình')
    args = p.parse_args()
    paths = sorted(args.input_folder.glob('*.geojson'))
    if not args.include_hull_inputs:
        paths = [p for p in paths if '_convex_hull_' not in p.name]
    if not paths:
        p.error('Không có kịch bản')
    raise SystemExit(execute(args, paths))
