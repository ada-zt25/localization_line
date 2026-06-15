def two_params_same(args):
    ns = Params()
    ns.add_param('count', type=int, default=0)
    ns.add_param('label', type=str, default='')
    ns.parse(args)
    return (ns.count, ns.label)