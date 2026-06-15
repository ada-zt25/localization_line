def default_when_omitted(args):
    params = Params()
    params.add_param('label', default='D')
    ns = params.parse(args)
    return ns.label