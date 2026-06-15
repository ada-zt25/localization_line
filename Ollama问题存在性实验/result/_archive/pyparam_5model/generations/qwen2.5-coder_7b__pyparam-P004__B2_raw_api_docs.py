def parse_list(args):
    params = Params()
    params.add_param('items', type='list')
    parsed_args = params.parse(args)
    return parsed_args.items