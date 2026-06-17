def two_reads_same_conf(profiles):
    config = ProfileConfig(profiles)
    config.switch('prod')
    x1 = config.conf.x
    x2 = config.conf.x
    return (x1, x2)