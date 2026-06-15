def parse_float(args):
    p = Params()
    p.add_param('ratio', type='float')
    ns = p.parse(args)
    return ns.ratio