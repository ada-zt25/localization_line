def profile_load_attr(profiles):
    with ProfileConfig.load(profiles, base='default').with_profile('default'):
        return conf.x