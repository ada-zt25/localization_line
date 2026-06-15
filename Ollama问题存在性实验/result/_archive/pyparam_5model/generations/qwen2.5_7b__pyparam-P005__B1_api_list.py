def required_present(args):
    p = Params()
    p.add_param('rr', type='int', default=None, required=True)
    parsed_args = p.parse(args)
    return parsed_args.rr