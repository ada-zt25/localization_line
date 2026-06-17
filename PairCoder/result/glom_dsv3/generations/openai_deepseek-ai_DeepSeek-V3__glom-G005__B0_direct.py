def safe_get(data, path):
    return glom(data, Coalesce(path, -1), skip_exc=PathAccessError)