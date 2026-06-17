def profile_load_attr(profiles):
    with profiles['default'].use_profile('default'):
        return profiles['default'].conf.x