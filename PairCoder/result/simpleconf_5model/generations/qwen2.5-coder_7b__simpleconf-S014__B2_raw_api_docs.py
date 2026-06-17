def with_profile_keeps_current(profiles):
    conf = ProfileConfig(profiles)
    use_profile(conf, 'prod')
    with use_profile(conf, 'default'):
        pass
    return current_profile(conf)