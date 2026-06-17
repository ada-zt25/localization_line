from simpleconf import Config, ProfileConfig

def profile_value(profiles, profile):
    conf = ProfileConfig.load(profiles, base='default')
    with conf.with_profile(profile):
        return conf.x