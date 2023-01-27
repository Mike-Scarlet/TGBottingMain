
def RemoveNoneItemFromDict(d: dict):
  keys_to_remove = []
  for k, v in d.items():
    if v is None:
      keys_to_remove.append(k)
  for k in keys_to_remove:
    del d[k]