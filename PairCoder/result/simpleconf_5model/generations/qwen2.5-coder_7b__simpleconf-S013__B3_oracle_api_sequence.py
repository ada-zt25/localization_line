def use_then_with_restore(profiles):
    config = Config()
    prod_profile = profiles['prod']
    default_profile = profiles['default']

    # Load and switch to 'prod' profile persistently
    config.load(prod_profile)
    mid = config.x

    # Read conf.x inside a temporary 'default' profile context
    with config.with_profile(default_profile):
        after = config.x

    return mid, after