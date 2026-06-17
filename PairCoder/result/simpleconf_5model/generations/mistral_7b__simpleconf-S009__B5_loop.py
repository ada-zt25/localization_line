def use_profile_same_conf(profiles, profile):
    with ProfileConfig.load(profiles, base='default').with_profile(profile) as config:
        return config['x']