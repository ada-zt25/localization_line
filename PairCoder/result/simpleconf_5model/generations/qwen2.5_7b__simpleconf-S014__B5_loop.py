from simpleconf import ProfileConfig

def with_profile_keeps_current(profiles):
    # Load the 'prod' profile configuration
    config = ProfileConfig.load(profiles, base='default')
    
    # Persistently switch to the 'prod' profile
    ProfileConfig.use_profile(config, 'prod')
    
    # Enter a temporary context for using 'default' profile
    with ProfileConfig.with_profile(config, 'default'):
        pass
    
    # Return the current active profile name, which should still be 'prod'
    return ProfileConfig.current_profile(config)