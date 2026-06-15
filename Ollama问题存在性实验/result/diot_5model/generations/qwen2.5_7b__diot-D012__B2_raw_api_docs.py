def thaw_is_temporary(data, key, val):
    from contextlib import contextmanager
    
    @contextmanager
    def temporary_thaw(diot_data):
        temp_diot = diot_data.copy()
        try:
            yield temp_diot
        finally:
            temp_diot.freeze()
    
    original_diot = OrderedDiot(data)
    with temporary_thaw(original_diot) as d:
        d[key] = val
    return original_diot.freeze()