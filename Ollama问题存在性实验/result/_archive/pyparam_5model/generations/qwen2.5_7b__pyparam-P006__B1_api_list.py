def default_when_omitted(args):
    p = Params()
    p.add_param('count', type='int', required=True)
    p.add_param('label', type='str', default='D')
    ns = p.parse(args)
    return ns.label