import simpleconf

def with_profile_keeps_current(profiles):
    current_profile = profiles.active_profile()
    profiles.switch('prod')
    with profiles.with_profile('default'):
        result = profiles.active_profile()
    profiles.switch(current_profile)
    return result