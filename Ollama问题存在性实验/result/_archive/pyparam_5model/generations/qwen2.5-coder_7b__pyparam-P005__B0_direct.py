def required_present(args):
    p = Params(POSITIONAL('rr', int))
    p.parse(args)
    return p['rr']