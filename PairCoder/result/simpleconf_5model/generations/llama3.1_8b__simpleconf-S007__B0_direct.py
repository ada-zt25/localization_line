def profile_load_attr(profiles):
    config = Config()
    profiles.load(config)
    return getattr(profiles, 'default').conf.x