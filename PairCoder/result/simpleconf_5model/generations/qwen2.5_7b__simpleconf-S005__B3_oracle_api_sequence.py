def active_profile_name(profiles, profile):
    ProfileConfig.load(profiles)
    ProfileConfig.switch_to(profile)
    return ProfileConfig.active_profile_name()