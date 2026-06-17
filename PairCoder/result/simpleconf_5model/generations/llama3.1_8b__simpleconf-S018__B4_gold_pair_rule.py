def two_reads_same_conf(profiles):
    config = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(config, 'prod')
    x1 = config.conf.x
    with ProfileConfig.with_profile(config, 'prod'):
        x2 = config.conf.x
    return (x1, x2)