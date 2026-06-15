def parse_then_use(args):
    p = Params()
    p.count = int
    parsed_args = POSITIONAL.parse_args(args)
    return parsed_args.count * 2