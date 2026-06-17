from simpleconf import Config, ProfileConfig

def use_survives_with(profiles):
    with profiles['default']:
        config = Config(profiles)
        config.switch('prod')
        result = config.x
        config.switch('default')
    return result