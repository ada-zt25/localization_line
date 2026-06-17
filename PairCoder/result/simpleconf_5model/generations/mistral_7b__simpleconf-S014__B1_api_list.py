from simpleconf import Config, ProfileConfig

def with_profile_keeps_current(profiles):
    # Load profiles config and switch to 'prod' persistently
    prod_config = ProfileConfig.load(profiles, base='default').use_profile('', 'prod')

    # Enter temporary context with default profile
    with prod_config.with_profile('default'):
        pass

    # Exit context and return current active profile name
    return prod_config.current_profile()