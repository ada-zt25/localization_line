from simpleconf import Config, ProfileConfig

def use_then_with_restore(profiles):
    with profiles['prod'].load() as conf_prod:
        mid = conf_prod.x

    with ProfileConfig(profiles)('default').with_persistent():
        with conf_prod.with_temporary():
            after = conf_prod.x

    return (mid, after)