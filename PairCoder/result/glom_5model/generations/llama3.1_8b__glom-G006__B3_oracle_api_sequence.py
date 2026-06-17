def coalesce_get(data):
    return glom.glom(
        data,
        Coalesce('primary', 'backup')
    )