def parse_then_use(args):
    p = Params()
    p.add_param('count', type='int', required=True)
    ns = p.parse(args)
    return ns.count * 2