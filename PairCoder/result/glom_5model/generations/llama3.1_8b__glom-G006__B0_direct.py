def coalesce_get(data):
    return glom.coalesce(
        data['primary'],
        data['backup']
    )