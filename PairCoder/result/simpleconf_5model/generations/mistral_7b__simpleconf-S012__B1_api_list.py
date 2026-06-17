from simpleconf import Config, ProfileConfig

def with_profile_temporary(profiles, profile):
    default_config = Config()
    initial_x = default_config.get('x', None)

    with ProfileConfig.load(profiles, base='default').with_profile(profile):
        inside_x = default_config.get('x', None)

    final_x = default_config.get('x', None)

    return (initial_x, inside_x, final_x)