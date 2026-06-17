def two_reads_same_conf(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    with ProfileConfig.with_profile(conf, 'prod'):
        x1 = conf.x
        x2 = conf.x
    return (x1, x2)