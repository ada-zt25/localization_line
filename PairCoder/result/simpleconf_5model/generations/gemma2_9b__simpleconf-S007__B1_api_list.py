def profile_load_attr(profiles):
  with ProfileConfig.with_profile(Config(), 'default'):
    return Config().x