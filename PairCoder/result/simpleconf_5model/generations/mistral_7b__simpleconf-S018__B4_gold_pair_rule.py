from simpleconf import Config, ProfileConfig

def two_reads_same_conf(profiles):
    conf = ProfileConfig.load(profiles, base='default')
    with conf.with_profile('prod'):
        x1 = conf.x
        x2 = conf.x
    return (x1, x2)