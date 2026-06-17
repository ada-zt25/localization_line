from simpleconf import Config, ProfileConfig

def two_reads_same_conf(profiles):
    config = Config(profiles)
    profile = ProfileConfig(config, 'prod')
    x1 = profile.conf.x
    x2 = profile['x']
    return (x1, x2)