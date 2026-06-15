def parse_two_fields(args):
    params = Params()
    params.add_param('count', type='int')
    params.add_param('label', type='str')
    ns = params.parse(args)
    return (ns.count, ns.label)