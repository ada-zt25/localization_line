def use_profile_same_conf(profiles, profile):
    config = Config.load(profiles)
    with ProfileConfig.use_profile(config, profile):
        return current_profile(config) == profile and config.conf.x == 'x'