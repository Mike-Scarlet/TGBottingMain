
class ParsedCommand:
  def __init__(self) -> None:
    self.command_strs = []

  def ParseCommand(self, s: str):
    if not isinstance(s, str):
      return
    self.command_strs = s.split(" ")

  def GetCommandKey(self):
    if len(self.command_strs) < 1:
      return None
    return self.command_strs[0]

  def GetParamCount(self):
    str_count = len(self.command_strs)
    if str_count < 1:
      return 0
    else:
      return str_count - 1

  def GetStringParam(self, param_idx):
    try:
      return self.command_strs[param_idx + 1]
    except:
      return None

  def GetIntParam(self, param_idx):
    try:
      return int(self.GetStringParam(param_idx))
    except:
      return None

  def GetFloatParam(self, param_idx):
    try:
      return float(self.GetStringParam(param_idx))
    except:
      return None

  def GetBoolParam(self, param_idx):
    try:
      param_real_content = self.GetStringParam(param_idx)
      if param_real_content == "true":
        return True
      elif param_real_content == "false":
        return False
      else:
        return None
    except:
      return None