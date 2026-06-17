def double_use_persistent(profiles):
    config = Config()
    profile_config = ProfileConfig('default', profiles)
    config.load_profile(profile_config)
    config.switch_to('prod')
    config.save()
    config.switch_to('default')
    config.save()
    return config.x