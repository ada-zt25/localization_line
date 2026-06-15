def two_reads_same_conf(profiles):
    pc = ProfileConfig(profiles, 'dev')
    pc.switch_to('prod')
    x1 = pc.read_conf('x')
    x2 = pc.read_conf('x')
    return (x1, x2)