def two_reads_same_conf(profiles):
    conf = ProfileConfig.load(profiles)
    ProfileConfig.use_profile(conf, 'prod')
    x1 = conf.x
    ProfileConfig.use_profile(conf, 'prod')  # Switch back to ensure the second read is from the same config
    x2 = conf.x
    return (x1, x2)