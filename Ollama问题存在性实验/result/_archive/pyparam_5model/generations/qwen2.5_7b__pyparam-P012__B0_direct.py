from pyparam import Params

def two_params_same(args):
    p = Params()
    p.add('count', POSITIONAL, type=int)
    p.add('label', POSITIONAL, type=str)
    ns = p.parse_args(args)
    return (ns.count, ns.label)