from simpleconf import ProfileConfig

def profile_value(profiles, profile):
    config = ProfileConfig(profiles)
    return config[profile].x