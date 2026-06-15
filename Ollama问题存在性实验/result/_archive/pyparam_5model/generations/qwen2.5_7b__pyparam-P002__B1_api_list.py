def parse_float(args):
    p = Params()
    p.add_param('ratio', type='float', default=None, required=False)
    ns = p.parse(args)
    return float(getattr(ns, 'ratio'))