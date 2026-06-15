def parse_list(args):
    p = Params()
    p.add_param('items', type='list')
    ns = p.parse(args)
    return ns.items