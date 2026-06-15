from pyparam import Params

def parse_two_fields(args):
    p = Params()
    p.add('count', type=int, positional=POSITIONAL)
    p.add('label', type=str)
    ns = p.parse_args(args)
    return (ns.count, ns.label)