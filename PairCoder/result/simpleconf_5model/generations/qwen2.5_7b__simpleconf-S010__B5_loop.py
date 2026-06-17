def mutate_then_read(data, key, val):
    conf = data  # Ensure we are working with the same object
    conf[key] = val  # Mutate the configuration
    return conf[key]  # Read and return the mutated value