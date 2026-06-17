def use_profile_same_conf(profiles, profile):
    pc = ProfileConfig.load(profiles)
    pc.switch_profile(profile)
    return pc.read('conf.x')