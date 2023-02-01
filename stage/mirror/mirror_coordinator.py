
from message.all_chat_messages_manager import AllChatMessageManager
from sql.mirror.mirror_coordinator_sql import *
import os
import asyncio

class MirrorCoordinator:
  def __init__(self, 
               mirror_coordinator_work_folder: str,
               all_chat_message_manager: AllChatMessageManager) -> None:
    self._mirror_coordinator_work_folder = mirror_coordinator_work_folder
    self._all_chat_message_manager = all_chat_message_manager

    self._db_access_lock = asyncio.Lock()

    self._conn = None
    self._op = None

  async def Initiate(self):
    if self._mirror_coordinator_work_folder is None:
      raise ValueError("self._mirror_coordinator_work_folder is None")
    if self._all_chat_message_manager is None:
      raise ValueError("self._all_chat_message_manager is None")

    db_path = os.path.join(self._mirror_coordinator_work_folder, "coordinator.db")
    async with self._db_access_lock:
      self._conn = SQLite3Connector(
        db_path,
        mirror_coordinator_table_structure
      )
      self._conn.Connect(do_check=False)
      self._conn.TableValidation()
      self._op = SQLite3Operator(self._conn)

    await self._HandleExistTasks(self)

  async def _HandleExistTasks(self):
    select_result = self._op.SelectFieldFromTable("*", "MirrorTasks")
    