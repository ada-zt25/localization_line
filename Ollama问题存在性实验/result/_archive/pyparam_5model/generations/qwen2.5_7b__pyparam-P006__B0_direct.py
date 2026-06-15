from pyparam import Params

def default_when_omitted(args):
    p = Params()
    p.add('count', help='Count value')
    p.add('label', 'D', help='Label value with default D')
    ns = p.parse_args(args)
    return ns.label