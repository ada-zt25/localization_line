def mutate_then_read(data, key, val):
    conf = Config.load(data)

    def with_profile_context():
        profile = current_profile = conf.current_profile(conf)
        conf.use_profile(conf, 'temp')
        conf[key] = val
        result = conf[key]
        conf.with_profile(conf, profile)
        return result

    with with_profile_context() as _:
        pass