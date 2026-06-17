def coalesce_get(data, primary, backup=None):
    try:
        result = glom(data, Coalesce('primary', 'backup'))
    except PathAccessError:
        if backup is None:
            raise
        result = backup
    return result