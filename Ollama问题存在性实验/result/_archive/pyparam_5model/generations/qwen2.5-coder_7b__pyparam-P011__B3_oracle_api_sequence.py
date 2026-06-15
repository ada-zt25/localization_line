def param_on_same_params(args):
    p = Params()
    p.add_param('count')
    ns = p.parse(args)
    return ns.count