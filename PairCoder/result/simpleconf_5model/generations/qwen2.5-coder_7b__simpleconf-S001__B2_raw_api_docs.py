def merge_get(base, override, key):
    with ProfileConfig(base) as conf:
        use_profile(conf, 'default')
        base_config = Config.load(conf)
        with ProfileConfig(override) as conf:
            use_profile(conf, 'default')
            override_config = Config.load(conf)
        merged_config = base_config + override_config
        return getattr(merged_config, key)