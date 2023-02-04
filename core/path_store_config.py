
from python_general_lib.interface.json_serializable import *

class PathStoreConfig(IJsonSerializable):
  """ the current user telegram info """
  def __init__(self) -> None:
    self.all_chat_db_store_folder = None
    self.mirror_coordinator_work_folder = None

  def FromJson(self, j):
    AutoObjectFromJsonHander(self, j)

if __name__ == "__main__":
  pass