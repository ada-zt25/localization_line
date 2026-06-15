def use_survives_with(profiles):
    conf = ProfileConfig.load(profiles)
    prod_value = conf.prod.x
    
    with profiles.use_profile('default'):
        assert profiles.current_profile() == 'default'
    
    assert profiles.current_profile() == 'prod'
    return conf.prod.x