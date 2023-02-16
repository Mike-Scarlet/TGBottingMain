
from utils.single_db_serializable_object import *
from http_bots.permission_management.permission_sql_definition import *
import threading

class PermissionDatabase(SingleDBSerializableObject):
  def __init__(self, db_path: str = None) -> None:
    super().__init__(db_path, permission_db_table_structure)
    self.user_id_permission_dict = {}
    self.lock = threading.Lock()

  def Initiate(self):
    super().InitiateDB()
    select_result = self._op.SelectFieldFromTable("*", "Messages")
    for d in select_result:
      self.user_id_permission_dict[d["user_id"]] = d["permission_value"]

  def GetPermission(self, user_id):
    return self.user_id_permission_dict.get(user_id, None)

  def SetPermission(self, user_id, permission_value):
    """ the user should call commit outside """
    with self.lock:
      self.user_id_permission_dict[user_id] = permission_value
      self._op.InsertDictToTable({
        "user_id": user_id, 
        "permission_value": permission_value
        }, "Messages", "OR UPDATE")