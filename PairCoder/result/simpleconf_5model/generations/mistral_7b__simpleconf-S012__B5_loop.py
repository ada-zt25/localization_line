def with_profile_temporary(profiles, profile):
    original_profile = Config.current()

    def inner():
        Config.use(ProfileConfig.load(profiles, base='default'))
        with ProfileConfig.with_profile(Config(), profile):
            conf_inside = Config().conf.x
        Config().use(ProfileConfig.load(profiles, base=original_profile))
        conf_after = Config().conf.x
        return conf_inside, conf_after

    return inner()