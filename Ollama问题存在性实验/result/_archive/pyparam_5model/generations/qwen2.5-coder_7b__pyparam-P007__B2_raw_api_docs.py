def parse_given(args):
    ns = Params()
    ns.add_param('count', type=int, default=0)
    return ns.parse(args).count