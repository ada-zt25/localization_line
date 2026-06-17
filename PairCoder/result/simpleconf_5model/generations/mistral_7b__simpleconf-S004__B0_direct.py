from simpleconf import Config, ProfileConfig

def profile_value(profiles, profile):
    config = Config(profiles)
    return config[profile].x