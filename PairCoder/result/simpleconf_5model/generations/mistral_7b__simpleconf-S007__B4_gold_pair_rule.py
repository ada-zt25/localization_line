def profile_load_attr(profiles):
    with ProfileConfig.load(profiles).with_profile('default'):
        return ProfileConfig.current_profile()['x']