def nested_is_diot(data):
  d = Diot(data, diot_transform='safe', diot_nest=True, diot_frozen=False)
  return d.x