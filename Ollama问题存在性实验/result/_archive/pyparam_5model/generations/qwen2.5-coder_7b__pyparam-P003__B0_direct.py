def parse_str(args):
    params = Params([POSITIONAL('name', str)])
    parsed_args = params.parse(args)
    return parsed_args['name']