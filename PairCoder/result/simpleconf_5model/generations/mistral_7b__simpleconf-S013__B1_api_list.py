from simpleconf import Config, ProfileConfig

def use_then_with_restore(profiles):
    with ProfileConfig.load(profiles, base='default').use_profile('default') as conf:
        mid = conf['x']

    with ProfileConfig.load({'prod': profiles['prod']}).with_profile('prod') as conf:
            after = conf['x']

    return mid, after