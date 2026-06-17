from simpleconf import ProfileConfig

def profile_load_attr(profiles):
    conf = ProfileConfig(profiles)
    conf.load()
    return conf.x