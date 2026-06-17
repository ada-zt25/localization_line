import simpleconf

def merge_three(a, b, c, key):
    with simpleconf.ProfileConfig(base='default').with_profile('merged'):
        simpleconf.load([simpleconf.Diot(a), simpleconf.Diot(b), simpleconf.Diot(c)], loader=simpleconf.Loaders.merge)
        profile = simpleconfig.current_profile('merged')
        return simpleconfig.ProfileConfig(base='merged').use_profile(profile).get(key, None)