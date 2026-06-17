def active_profile_name(profiles, profile):
    Config.load()
    profiles.select(profile)
    return profiles.active.name