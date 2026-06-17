def coalesce_get(data, primary, backup):
    return Coalesce('primary', 'backup')(glom, data)