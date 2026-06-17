def coalesce_get(data, primary, backup):
    return Coalesce('primary', Assign(primary, data), backup)(data)