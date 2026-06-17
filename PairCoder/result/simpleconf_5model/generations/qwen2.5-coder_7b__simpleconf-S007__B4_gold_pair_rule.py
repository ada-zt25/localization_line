def profile_load_attr(profiles):
    conf = ProfileConfig.load(profiles)
    return conf.x