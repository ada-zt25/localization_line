from simpleconf import Config, ProfileConfig

def profile_value(profiles, profile, conf_key='x'):
    diot = Config.load(*profiles)
    base_config = ProfileConfig.load(profiles, base='default')
    with base_config.with_profile(diot, profile):
        return base_config[conf_key]