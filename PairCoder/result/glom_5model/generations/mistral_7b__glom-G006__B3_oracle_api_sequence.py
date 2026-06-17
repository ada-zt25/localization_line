from glom import Coalesce, glom

def coalesce_get(data, primary=None, backup=None):
    return Coalesce(glom(data, primary), glom(data, backup))