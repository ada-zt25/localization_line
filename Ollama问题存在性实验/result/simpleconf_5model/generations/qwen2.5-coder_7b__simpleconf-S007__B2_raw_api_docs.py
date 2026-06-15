def profile_load_attr(profiles):
    conf = Config()
    for profile in profiles:
        ProfileConfig(conf, profile)
    return getattr(conf, 'x', None)