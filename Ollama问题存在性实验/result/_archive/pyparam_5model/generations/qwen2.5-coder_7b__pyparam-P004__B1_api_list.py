def parse_list(args):
    p = Params()
    p.add_param('items', type='list', default=None, required=False)
    ns = p.parse(args)
    return getattr(ns, 'items', [])