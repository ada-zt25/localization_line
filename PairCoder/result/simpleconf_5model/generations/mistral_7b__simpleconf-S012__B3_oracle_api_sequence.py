import simpleconf

def with_profile_temporary(profiles, profile):
    original = simpleconf.load(profiles)
    try:
        with simpleconf.with_profile(profiles, profile):
            inside = simpleconf.load(profiles).x
    finally:
        simpleconf.load(original.profiles)
    after = simpleconf.load(original.profiles).x
    return inside, after