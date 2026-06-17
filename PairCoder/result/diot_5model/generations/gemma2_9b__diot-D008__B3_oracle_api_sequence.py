def todict_then_index(data):
  d = Diot(data)
  return d.to_dict()["x"]["y"]