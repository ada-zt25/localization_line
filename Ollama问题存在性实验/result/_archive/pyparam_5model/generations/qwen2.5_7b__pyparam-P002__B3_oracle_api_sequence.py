from pyparam import Params

def parse_float(args):
    p = Params()
    p.add_param('ratio', type='float')
    parsed = p.parse(args)
    return parsed.ratio