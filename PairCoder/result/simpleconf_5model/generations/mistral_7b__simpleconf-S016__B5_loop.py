import contextlib

def use_survives_with(profiles):
    with ProfileConfig.load(profiles, base='default').with_profile('default') as conf:
        conf.use_profile('prod')
        result = conf.x
    return result