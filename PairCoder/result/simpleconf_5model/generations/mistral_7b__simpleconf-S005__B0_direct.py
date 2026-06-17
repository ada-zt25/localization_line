from simpleconf import Config, ProfileConfig

def active_profile_name(profiles, profile):
    config = Config(profiles)
    config.switch_to(profile)
    return config.active_profile