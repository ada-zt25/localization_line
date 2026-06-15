def parse_given(args):
    p = Params()
    p.add_param('count', type='int')
    ns = p.parse(args)
    return ns.count