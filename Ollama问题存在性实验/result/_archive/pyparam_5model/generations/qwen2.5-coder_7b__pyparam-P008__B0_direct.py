def parse_then_attr(args):
    params = Params(count=int)
    namespace = params.parse_args(args)
    return namespace.count