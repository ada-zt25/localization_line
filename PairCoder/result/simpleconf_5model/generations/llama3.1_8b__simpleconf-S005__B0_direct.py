def active_profile_name(profiles, profile):
    Config.load_profiles(profiles)
    Config.switch_to(profile)
    return Config.active_profile.name