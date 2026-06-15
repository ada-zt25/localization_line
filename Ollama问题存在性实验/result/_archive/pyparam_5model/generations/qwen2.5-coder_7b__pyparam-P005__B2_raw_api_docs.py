def required_present(args):
    p = Params()
    p.add_param('rr', type=int, required=True)
    parsed_args = p.parse(args)
    return getattr(parsed_args, 'rr')