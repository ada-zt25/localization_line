from simpleconf import Config, ProfileConfig
from diot import Diot

def merge_then_nested(data, k1, k2):
    merged_config = Config.load(*data)
    return merged_config[k1][k2]