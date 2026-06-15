def parse_int(args):
    params = Params()
    params.add_param('--count', type='int', default=0, required=True)
    parsed_args = params.parse(args)
    return int(getattr(parsed_args, 'count'))