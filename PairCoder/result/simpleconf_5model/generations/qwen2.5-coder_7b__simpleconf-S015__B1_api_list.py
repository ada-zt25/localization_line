def nested_with_profiles(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    
    with ProfileConfig.with_profile(conf, 'prod') as prod_conf:
        a = prod_conf.x
        
        with ProfileConfig.with_profile(prod_conf, 'default') as default_conf:
            b = default_conf.x
        
        c = prod_conf.x
    
    return (a, b, c)