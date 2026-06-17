import simpleconf

def merge_then_nested(data, k1, k2):
    with ProfileConfig.load(data).with_profile('default'):
        current_profile = ProfileConfig.current_profile()
        Config.load([ProfileConfig.load({current_profile: {}}, base=current_profile)])
        Config.load([data])
        nested_value = data[k1][k2]
        with ProfileConfig.with_profile(current_profile, k1):
            return nested_value