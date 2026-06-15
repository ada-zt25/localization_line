def merge_get(base: Config, override: ProfileConfig, key):
    # Load base config
    merged_config = base.load()
    
    # Switch to override profile temporarily and load it
    with override.with_profile('default'):
        override_config = override.load()
    
    # Merge override into base
    merged_config.update(override_config)
    
    # Return the value for key
    return merged_config[key]