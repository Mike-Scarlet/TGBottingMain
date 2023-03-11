
from http_bots.bot_channel_chat.bot_channel_chat_models import *
from python_general_lib.interface.json_serializable import *
from utils.async_single_db_auto_commit_serializable_object import *

class UserStatusDatabase(AsyncSingleDBAutoCommitSerializableObject):
  def __init__(self, db_path: str = None) -> None:
    super().__init__(db_path, user_status_table_structure)

  async def Initiate(self, loop: asyncio.AbstractEventLoop):
    await super().Initiate(loop)

  async def GetAllUserStatus(self):
    async with self._lock:
      all_status = []
      query_results = self._op.SelectFieldFromTable("*", "UserStatus")
      for result in query_results:
        single_status = ChannelChatUserStatus()
        AutoObjectFromJsonHander(single_status, result)
        all_status.append(single_status)
    return all_status

  async def AddUserStatus(self, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.InsertDictToTable(
        {
          "user_id": user_status.user_id,
          "permission": user_status.permission,
          "status": user_status.status,
          "join_time": user_status.join_time,
          "last_active_time": user_status.last_active_time,
          "active_expire_time": user_status.active_expire_time,
          "fake_name": user_status.fake_name,
        }, 
        "UserStatus", "OR IGNORE")
      await self.AutoCommitAfter(5.0)

  async def UpdateUserJoinTime(self, user_id, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"join_time": user_status.join_time}, 
        "UserStatus", 
        "user_id = {}".format(user_id))
      await self.AutoCommitAfter(5.0)

  async def UpdateUserFakeName(self, user_id, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"fake_name": user_status.fake_name}, 
        "UserStatus", 
        "user_id = {}".format(user_id))
      await self.AutoCommitAfter(5.0)

  async def UpdateUserLastActiveAndExpireTime(self, user_id, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {
          "last_active_time": user_status.last_active_time,
          "active_expire_time": user_status.active_expire_time,
        }, 
        "UserStatus", 
        "user_id = {}".format(user_id))
      await self.AutoCommitAfter(5.0)
  
  async def UpdateUserCurrentStatus(self, user_id, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"status": user_status.status}, 
        "UserStatus", 
        "user_id = {}".format(user_id))
      await self.AutoCommitAfter(5.0)

  async def UpdateUserPermission(self, user_id, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"permission": user_status.permission}, 
        "UserStatus", 
        "user_id = {}".format(user_id))
      await self.AutoCommitAfter(5.0)

class FromMessagesManageDatabase(AsyncSingleDBAutoCommitSerializableObject):
  def __init__(self, db_path: str = None) -> None:
    super().__init__(db_path, from_messages_table_structure)
    self._index_assigner = 0

  async def Initiate(self, loop: asyncio.AbstractEventLoop):
    await super().Initiate(loop)
    raw_sel_result = self._op.RawSelectFieldFromTable("max(task_index)", "FromMessages")
    try:
      value = raw_sel_result[0][0]
      if value is not None:
        self._index_assigner = value + 1
    except:
      pass

  async def AddForwardTask(self, forward_task: ForwardTask):
    forward_task.task_index = self._index_assigner
    self._index_assigner += 1
    insert_dict = {
      "task_index": forward_task.task_index,
      "from_user_id": forward_task.from_user_id,
      "from_message_id": forward_task.from_message_id,
      "file_unique_id": forward_task.file_unique_id,
      "forward_status": kForwardStatusInQueue,
      "add_time": time.time(),
    }
    async with self._lock:
      self._op.InsertDictToTable(insert_dict, "FromMessages")
      await self.AutoCommitAfter(4.0)

  async def GetFailForwardTasks(self):
    async with self._lock:
      all_fail_dict = self._op.SelectFieldFromTable("*", "FromMessages", "forward_status = 0")
    result = []
    for fail_dict in all_fail_dict:
      task = ForwardTask()
      task.task_index = fail_dict["task_index"]
      task.from_user_id = fail_dict["from_user_id"]
      task.from_message_id = fail_dict["from_message_id"]
      task.file_unique_id = fail_dict["file_unique_id"]
      result.append(task)
    return result

  async def GetForwardTaskByTaskIndex(self, task_index):
    async with self._lock:
      query_result = self._op.SelectFieldFromTable("*", "FromMessages", "task_index = {}".format(task_index))
    return query_result
    
  async def SetSuccessForForwardTask(self, forward_task: ForwardTask):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"forward_status": kForwardStatusDone}, 
        "FromMessages", 
        "from_user_id = {} and from_message_id = {}".format(
            forward_task.from_user_id, forward_task.from_message_id))
      await self.AutoCommitAfter(4.0)

  async def SetInvalidForForwardTask(self, forward_task: ForwardTask):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"forward_status": kForwardStatusInvalid}, 
        "FromMessages", 
        "from_user_id = {} and from_message_id = {}".format(
            forward_task.from_user_id, forward_task.from_message_id))
      await self.AutoCommitAfter(4.0)