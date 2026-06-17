from simpleconf import Config, ProfileConfig

def profile_value(profiles, profile, conf_key):
    diot = Config.load(profiles)
    active_profile = current_profile(diot)
    with diot.with_profile(profile):
        active_profile = current_profile(diot)
        return getattr(diot, conf_key)