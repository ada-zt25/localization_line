def parse_two_fields(args):
    p = Params()
    p.add_param('count', type='int')
    p.add_param('label', type='str')
    ns = p.parse(args)
    return (ns.count, ns.label)