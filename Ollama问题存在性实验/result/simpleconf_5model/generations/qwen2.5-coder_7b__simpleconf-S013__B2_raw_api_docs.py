def use_then_with_restore(profiles):
    conf = Config.load(*profiles)
    prod_value = conf.x
    with ProfileConfig(conf, 'default') as default_conf:
        mid = default_conf.x
    after = conf.x
    return (mid, after)