def parse_given(args):
    p = Params(count=0)
    p.parse_args(args, POSITIONAL)
    return p.count