def with_profile_temporary(profiles, profile):
    with profiles.load(profile) as config:
        inside = config['conf.x']
    after = Config()['conf.x']
    return (inside, after)