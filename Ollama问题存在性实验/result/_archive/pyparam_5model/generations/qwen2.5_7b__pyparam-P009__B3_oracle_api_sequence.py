from pyparam import Params

def parse_two_fields(args):
    p = Params()
    p.add_param('count', int, POSITIONAL)
    p.add_param('label', str, POSITIONAL)
    ns = p.parse(args)
    return (ns.count, ns.label)