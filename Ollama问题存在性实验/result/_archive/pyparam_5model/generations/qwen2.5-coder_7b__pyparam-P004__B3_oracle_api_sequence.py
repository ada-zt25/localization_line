def parse_list(args):
    params = Params()
    params.add_param('items', type='list')
    params.parse(args)
    return params.items