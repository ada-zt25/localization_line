def param_on_same_params(args):
    p = Params()
    p.add('count', type=int)
    ns = p.parse_args(args, POSITIONAL)
    return ns.count