def parse_then_use(args):
    params = Params()
    params.add_param('count', type='int')
    parsed_args = params.parse(args)
    return parsed_args.count * 2