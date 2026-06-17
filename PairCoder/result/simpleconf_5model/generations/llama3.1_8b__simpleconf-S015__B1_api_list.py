def nested_with_profiles(profiles):
    with ProfileConfig.load(profiles, base='default') as config:
        config.use_profile(config, 'prod')
        a = config['x']
        
        with config.with_profile('default'):
            b = config['x']
            
        c = config['x']
        
    return (a, b, c)