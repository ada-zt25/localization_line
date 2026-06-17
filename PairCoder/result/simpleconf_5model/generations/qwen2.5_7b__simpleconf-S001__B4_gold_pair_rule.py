from simpleconf import Config, ProfileConfig
import diot

def merge_get(base, override, key):
    merged_config = Config.load(base, override)
    return merged_config[key]