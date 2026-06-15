def parse_str(args):
    p = Params()
    p.add_param('name', type='str')
    parsed = p.parse(args)
    return parsed.name