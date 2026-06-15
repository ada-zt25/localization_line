def parse_given(args):
    ns = Params()
    ns.add_param('count', type='int')
    ns.parse(args)
    return ns.count