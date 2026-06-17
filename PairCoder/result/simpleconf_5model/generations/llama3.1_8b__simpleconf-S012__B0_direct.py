def with_profile_temporary(profiles, profile):
    with profiles[profile]:
        inside = Config().read('conf.x')
    after = Config().read('conf.x')
    return (inside, after)