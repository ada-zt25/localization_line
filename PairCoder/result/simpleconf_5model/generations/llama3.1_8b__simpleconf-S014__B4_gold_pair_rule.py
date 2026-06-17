def with_profile_keeps_current(profiles):
    profile_config = ProfileConfig.load(profiles, base='default')
    profile_config.use_profile(profile_config.current_config, 'prod')

    with profile_config.with_profile(profile_config.current_config, 'default'):
        pass  # do nothing in the temporary context

    return profile_config.current_profile(profile_config.current_config)