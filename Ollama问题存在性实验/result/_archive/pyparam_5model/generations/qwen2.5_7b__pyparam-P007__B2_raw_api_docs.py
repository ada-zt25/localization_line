def parse_given(args):
    p = Params()
    p.add_param('--count', type='int', default=0)
    ns = p.parse(args)
    return ns.count