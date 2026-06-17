from simpleconf import ProfileConfig

def use_profile_same_conf(profiles, profile):
    conf = profiles.load()
    ProfileConfig.use_profile(conf, profile)
    return conf.x