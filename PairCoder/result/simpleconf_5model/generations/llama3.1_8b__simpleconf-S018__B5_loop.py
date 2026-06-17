def two_reads_same_conf(profiles):
    config = ProfileConfig.load(profiles, base='default')
    config.use_profile(config, 'prod')  # switch active profile (persistent)
    with config.with_profile(config, 'prod'):  # context manager: switch temporarily
        x1 = config.conf.x
    x2 = config.conf.x
    return (x1, x2)