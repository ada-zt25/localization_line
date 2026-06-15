def parse_str(args):
    p = Params()
    p.add('name', type=str)
    for arg in args:
        if arg.startswith('--'):
            key = arg[2:]
            if '=' in key:
                key, value = key.split('=', 1)
                p.set(key, value)
            else:
                POSITIONAL[p.positional_count] = key
        else:
            p.set_positional(arg)
    return str(p.name)