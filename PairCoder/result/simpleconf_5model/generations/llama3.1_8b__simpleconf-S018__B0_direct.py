def two_reads_same_conf(profiles):
    profile = profiles['prod']
    config = ProfileConfig(profile)
    x1 = config.conf.x
    config.switch_to('prod')
    x2 = config.conf.x
    return (x1, x2)