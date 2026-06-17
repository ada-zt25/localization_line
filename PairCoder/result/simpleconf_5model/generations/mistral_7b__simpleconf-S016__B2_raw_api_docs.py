from simpleconf import Config, ProfileConfig

def use_survives_with(profiles):
    # Load profiles config with all given profiles
    loaded = ProfileConfig.load(*profiles)

    # Switch to 'prod' profile persistently
    loaded.use_profile('prod')

    # Enter a temporary context with the default profile
    with loaded.with_profile('default'):
        # Get and return the value of conf.x (which should be 'prod')
        conf_x = loaded.conf.x

    # Switch back to the previously active profile (should still be 'prod')
    loaded.use_profile(loaded.current_profile(loaded))

    return conf_x