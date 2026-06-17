def with_profile_keeps_current(profiles):
    prod_config = ProfileConfig.load(profiles, base='default')
    ProfileConfig.use_profile(prod_config, 'prod')

    with ProfileConfig.with_profile(prod_config, 'default'):
        pass  # do nothing in the temporary context

    return ProfileConfig.current_profile(prod_config)