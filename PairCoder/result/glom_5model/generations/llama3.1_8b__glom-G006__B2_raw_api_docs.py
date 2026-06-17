def coalesce_get(data):
    return Coalesce(
        Path('primary'),
        Path('backup')
    )(data)