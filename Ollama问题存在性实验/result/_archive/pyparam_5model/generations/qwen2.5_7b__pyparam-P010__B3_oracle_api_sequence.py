def parse_then_use(args):
    p = Params()
    p.add_param('count', type='int')
    parsed = p.parse(args)
    return parsed.count * 2