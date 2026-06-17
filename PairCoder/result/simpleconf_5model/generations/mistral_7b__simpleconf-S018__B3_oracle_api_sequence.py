import simpleconf

def two_reads_same_conf(profiles):
    config = simpleconf.load(profiles)
    config.set_profile('prod')
    x1 = config['x']
    x2 = config['x']
    return (x1, x2)