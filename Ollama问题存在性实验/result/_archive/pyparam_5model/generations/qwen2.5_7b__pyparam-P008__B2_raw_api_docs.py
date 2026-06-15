def parse_then_attr(args):
    params = Params()
    params.add_param('--count', type='int', default=1, required=True)
    parsed_args = params.parse(args)
    return parsed_args.count