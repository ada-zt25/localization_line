def use_profile_same_conf(profiles, profile):
  prof = ProfileConfig.load(profiles)
  prof.switch_to(profile)
  return prof.conf.x