def two_reads_same_conf(profiles):
    with ProfileConfig.load(profiles, base='default').with_profile('prod'):
        conf = ProfileConfig.load(profiles, base='default')
        x1 = conf['conf.x']
        conf.update({'conf': {'x': x1}})  # update the config with the first read value
        x2 = conf['conf.x']
    return (x1, x2)