def nested_with_profiles(profiles):
    config = Config()
    with ProfileConfig(config, 'prod') as conf:
        a = conf.x
        with ProfileConfig(conf, 'default') as inner_conf:
            b = inner_conf.x
        c = conf.x
    return (a, b, c)