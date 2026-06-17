def with_profile_keeps_current(profiles):
    Config.load(profiles)
    ProfileConfig.use_profile(Config, 'prod')
    with ProfileConfig.with_profile(Config, 'default'):
        pass
    return ProfileConfig.current_profile(Config)