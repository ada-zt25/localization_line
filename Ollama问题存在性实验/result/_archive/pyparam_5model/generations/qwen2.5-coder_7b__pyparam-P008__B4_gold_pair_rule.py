def parse_then_attr(args):
    p = Params()
    p.add_param('count', type='int', default=0, required=False)
    ns = p.parse(args)
    return ns.count