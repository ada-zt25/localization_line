def coalesce_get(data, primary, backup):
    return Coalesce(glom(data, primary), glom(data, backup))