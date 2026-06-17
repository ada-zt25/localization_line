def profile_load_attr(profiles):
    with profiles['default'].with_profile('default'):
        return conf.x