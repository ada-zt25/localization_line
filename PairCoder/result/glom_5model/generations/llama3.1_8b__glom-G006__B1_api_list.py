def coalesce_get(data):
    return glom.Coalesce(
        'primary',
        ('backup', glom.glom(data, 'backup')),
        default=None
    )(data)