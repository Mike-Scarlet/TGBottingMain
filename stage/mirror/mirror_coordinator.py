
from message.all_chat_messages_manager import AllChatMessageManager, kHistoryRetrieveFromLastMessage
from sql.mirror.mirror_coordinator_sql import *
import os
import asyncio

class SingleMirrorDistributeHandler:
  def __init__(self, 
               mirror_from_chat: str, 
               mirror_to_chat: str, 
               all_chat_message_manager: AllChatMessageManager) -> None:
    self._mirror_from_chat = mirror_from_chat
    self._mirror_to_chat = mirror_to_chat
    self._all_chat_message_manager = all_chat_message_manager

    self._replicate_insert_message_queue = asyncio.Queue(10)

  async def AddDistributeSourceMessage(self, message):
    pass

class MirrorCoordinator:
  def __init__(self, 
               mirror_coordinator_work_folder: str,
               all_chat_message_manager: AllChatMessageManager) -> None:
    self._mirror_coordinator_work_folder = mirror_coordinator_work_folder
    self._all_chat_message_manager = all_chat_message_manager

    self._db_access_lock = asyncio.Lock()

    self._conn = None
    self._op = None

    self._handler_access_lock = asyncio.Lock()
    self._mirror_from_chat_to_handlers_dict = {}

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
    select_results = self._op.SelectFieldFromTable("*", "MirrorTasks")
    for task_dict in select_results:
      if task_dict["is_active"] == 0:
        continue
      await self._AddMirrorDistribute(task_dict["from_chat_id"], task_dict["to_chat_id"])
    for task_dict in select_results:
      if task_dict["is_active"] == 0:
        continue
      await self._all_chat_message_manager.GeneralHistoryRetrieve(task_dict["from_chat_id"], kHistoryRetrieveFromLastMessage)

  async def _AddMirrorDistribute(self, from_chat_id, to_chat_id):
    pass