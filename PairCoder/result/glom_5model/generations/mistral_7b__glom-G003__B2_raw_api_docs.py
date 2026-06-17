from typing import List, Dict

def pluck_list(data):
    return list(glom(data, 'items.v'))