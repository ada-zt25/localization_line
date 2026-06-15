from pyparam import Params

def two_params_same(args):
    p = Params()
    p.add_param('count', POSITIONAL)
    p.add_param('label', POSITIONAL)
    ns = p.parse(args)
    return (ns.count, ns.label)