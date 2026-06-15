def two_reads_same_conf(profiles):
    conf = ProfileConfig.load(profiles)
    use_profile(conf, 'prod')
    x1 = conf.x
    _ = conf.x  # Reading conf.x again to simulate the second read
    return (x1, conf.x)