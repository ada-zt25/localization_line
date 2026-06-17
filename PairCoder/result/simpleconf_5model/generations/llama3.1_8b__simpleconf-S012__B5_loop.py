def with_profile_temporary(profiles, profile):
    config = ProfileConfig.load(profiles, base='default')
    with config.with_profile(conf=config, profile=profile):
        return (config['conf.x'],)
    return (config['conf.x'],)