
from python_general_lib.interface.json_serializable import *

class TelegramSessionConfig(IJsonSerializable):
  """ the current user telegram info """
  def __init__(self) -> None:
    self.api_hash = None
    self.api_id = None
    self.workdir = None
    self.phone_number = None

  def FromJson(self, j):
    AutoObjectFromJsonHander(self, j)

if __name__ == "__main__":
  sess = TelegramSessionConfig()
  sess.LoadFromJsonFile("/home/ubuntu/DevelopEnvironment/tools/misc/TelegramLocalBot/config/session.json")
  pass