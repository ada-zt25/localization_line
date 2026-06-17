from simpleconf import Config, ProfileConfig

def with_profile_keeps_current(profiles):
    config = Config(profiles)
    original_profile = config.active_profile

    with ProfileConfig(config, 'prod'):
        with ProfileConfig(config, 'default'):
            active_profile = config.active_profile

    return active_profile == 'prod' and original_profile == 'prod'