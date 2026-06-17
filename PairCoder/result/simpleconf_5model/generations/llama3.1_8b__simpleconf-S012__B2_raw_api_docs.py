def with_profile_temporary(profiles, profile):
    with profiles.with_profile(profile):
        inside = profiles.conf.x
    after = profiles.conf.x
    return (inside, after)