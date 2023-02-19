
"""
user info db
message process queue
"""

if __name__ == "__main__":
  import sys, os
  need_to_add_path = __file__
  for _ in range(3):
    need_to_add_path = os.path.dirname(need_to_add_path)
  sys.path.append(need_to_add_path)  # add root directory

from python_general_lib.environment_setup.logging_setup import *
from python_general_lib.interface.json_serializable import *
from utils.async_single_db_auto_commit_serializable_object import *
from http_bots.bot_channel_chat.bot_channel_chat_constants import *
import telegram
import telegram.ext
import os, time

class ForwardTask:
  def __init__(self) -> None:
    self.task_index = None
    self.from_user_id = None
    self.from_message_id = None
    self.file_unique_id = None

class ForwardCommand:
  task: ForwardTask
  def __init__(self) -> None:
    self.task = None
    self.to_user_id = None

class ChannelChatUserStatus:
  def __init__(self) -> None:
    self.user_id = None
    self.permission = kChatPermissionInvalidUser
    self.status = kChatStatusInactive
    self.join_time = 0
    self.last_active_time = 0

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

  async def UpdateUserLastActiveTime(self, user_id, user_status: ChannelChatUserStatus):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"last_active_time": user_status.last_active_time}, 
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

    
  async def SetSuccessForForwardTask(self, forward_task: ForwardTask):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"forward_status": kForwardStatusDone}, 
        "FromMessages", 
        "from_user_id = {} and from_message_id = {}".format(
            forward_task.from_user_id, forward_task.from_message_id))
      await self.AutoCommitAfter(4.0)

  async def SetFailForForwardTask(self, forward_task: ForwardTask):
    async with self._lock:
      self._op.UpdateFieldFromTable(
        {"forward_status": kForwardStatusInvalid}, 
        "FromMessages", 
        "from_user_id = {} and from_message_id = {}".format(
            forward_task.from_user_id, forward_task.from_message_id))
      await self.AutoCommitAfter(4.0)

class BotChannelChat:
  _user_status_dict: typing.Dict[int, ChannelChatUserStatus]
  def __init__(self, workspace_folder) -> None:
    self._logger = logging.getLogger("BotChannelChat")
    self._workspace_folder = workspace_folder
    self._from_message_db = None
    self._user_status_db = None
    self._user_status_dict_access_lock = asyncio.Lock()
    self._user_status_dict = {}
    self._forward_process_queue = asyncio.Queue(10000)  # max store 10000 messages
    self._tg_app = None
    self._loop_task = None
    self._active_user_count = 0
    self._command_forward_worker_count = 24
    self._command_forward_workers = []
    self._command_forward_queue = asyncio.Queue(1)

  def PrepareHandlers(self, app: telegram.ext.Application):
    app.add_handler(telegram.ext.CommandHandler("start", self.StartHandler))
    app.add_handler(telegram.ext.CommandHandler("join", self.JoinHandler))
    app.add_handler(telegram.ext.CommandHandler("current_status", self.CurrentStatusHandler))
    app.add_handler(telegram.ext.CommandHandler("get_chat_status", self.GetChatStatusHandler))
    app.add_handler(telegram.ext.CommandHandler("add_user", self.AddUserHandler))
    app.add_handler(
      telegram.ext.MessageHandler(telegram.ext.filters.PHOTO | telegram.ext.filters.VIDEO, self.MediaHandler)
      )

  async def Initiate(self, app: telegram.ext.Application):
    self._tg_app = app
    if self._workspace_folder is None:
      self._logger.error("workspace folder is None")
      raise ValueError("workspace folder is None")
    if not os.path.exists(self._workspace_folder):
      os.makedirs(self._workspace_folder)

    # do all initiate process here
    self._logger.info("initiate is called")
    
    loop = asyncio.get_event_loop()
    self._from_message_db = FromMessagesManageDatabase(os.path.join(self._workspace_folder, "from_message.db"))
    await self._from_message_db.Initiate(loop)

    self._user_status_db = UserStatusDatabase(os.path.join(self._workspace_folder, "user_status.db"))
    await self._user_status_db.Initiate(loop)

    all_user_status = await self._user_status_db.GetAllUserStatus()
    for st in all_user_status:
      st: ChannelChatUserStatus
      self._user_status_dict[st.user_id] = st
      if st.status == kChatStatusActive:
        self._active_user_count += 1

    self._loop_task = loop.create_task(self.ForwardWorkerLoop())

    for _ in range(self._command_forward_worker_count):
      self._command_forward_workers.append(loop.create_task(self.SimpleForwardWorker()))

    self._logger.info("initiate is finished")
    self._logger.info("start to handle histories")
    fail_tasks = await self._from_message_db.GetFailForwardTasks()
    for forward_task in fail_tasks:
      self._logger.info("add history forward task #{} : {} - {} - {}".format(
        forward_task.task_index, forward_task.from_user_id, forward_task.from_message_id, forward_task.file_unique_id))
      await self._forward_process_queue.put(forward_task)
    self._logger.info("history handle finished")

  async def PrepareStop(self, app: telegram.ext.Application):
    # do all clean process here
    pass

  """ handlers """
  async def StartHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    try:
      await update.message.reply_text(f'Hello {user.first_name}, your user id is {user.id}, send /join to join the chat, send /current_status to check your status')
    except:
      pass

  async def JoinHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    user_st = self._user_status_dict.get(user.id, None)
    if user_st is None:
      self._logger.info("inrecognized user {} - {} sent join".format(user.id, user.full_name))
      return
    if user_st.join_time == 0:
      await self.SetJoinTime(user_st)
    if user_st.permission in (kChatPermissionVIPUser, kChatPermissionAdminUser):
      await self.ActivateOrSetActiveTime(user_st, update)
    else:
      try:
        await update.message.reply_text(f'send a video or photo to activate')
      except:
        pass

  async def CurrentStatusHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    user_st = self._user_status_dict.get(user.id, None)
    if user_st is None:
      return
    try:
      await update.message.reply_text(f'your user id: {user_st.user_id}, your active status: {user_st.status != kChatStatusInactive}')
    except:
      pass

  async def GetChatStatusHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    user_st = self._user_status_dict.get(user.id, None)
    if user_st is None:
      return
    try:
      await update.message.reply_text(f'the process queue size is {self._forward_process_queue.qsize()}, the active user count is {self._active_user_count}')
    except:
      pass

  async def AddUserHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    user_st = self._user_status_dict.get(user.id, None)
    if user_st is None:
      return
    if user_st.permission != kChatPermissionAdminUser:
      return
    # parse user id
    try:
      user_id = int(update.effective_message.text.replace("/add_user ", ""))
      if user_id in self._user_status_dict:
        try:
          await update.message.reply_text('user already exists: {}'.format(user_id))
        except Exception as e:
          print(e)
          pass
      else:
        await self.AddNewUser(user_id)
    except:
      try:
        await update.message.reply_text('fail to add user: "{}"'.format(update.effective_message.text))
      except Exception as e:
        print(e)
        pass
      return
    try:
      await update.message.reply_text('user added: {}'.format(user_id))
      self._logger.info("admin {} added user: {}".format(user_st.user_id, user_id))
    except:
      pass

  async def MediaHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None:
      return
    # TODO: global status check
    # update user current status
    if update.effective_message.video is not None or update.effective_message.photo is not None:
      # current we only accept exist users
      user_st = self._user_status_dict.get(update.effective_chat.id, None)
      if user_st is None:
        return
      await self.ActivateOrSetActiveTime(user_st, update)
    forward_task = None
    if update.effective_message.video is not None:
      # add video
      forward_task = ForwardTask()
      forward_task.from_user_id = update.effective_chat.id
      forward_task.from_message_id = update.effective_message.message_id
      forward_task.file_unique_id = update.effective_message.video.file_unique_id
      # add to status store db
      await self._from_message_db.AddForwardTask(forward_task)
      await self._forward_process_queue.put(forward_task)
    if update.effective_message.photo is not None and len(update.effective_message.photo) > 0:
      valid_photo = update.effective_message.photo[-1]
      forward_task = ForwardTask()
      forward_task.from_user_id = update.effective_chat.id
      forward_task.from_message_id = update.effective_message.message_id
      forward_task.file_unique_id = valid_photo.file_unique_id
      # add to status store db
      await self._from_message_db.AddForwardTask(forward_task)
      await self._forward_process_queue.put(forward_task)
    if forward_task is not None:
      self._logger.info("add forward task #{} : {} - {} - {}".format(
        forward_task.task_index, forward_task.from_user_id, forward_task.from_message_id, forward_task.file_unique_id))

  """ worker loop """
  async def ForwardWorkerLoop(self):
    while True:
      get_result: ForwardTask = await self._forward_process_queue.get()
      if get_result is None:
        break
      async with self._user_status_dict_access_lock:
        user_status_list = list(self._user_status_dict.items())
      for user_id, status in user_status_list:
        if status.status in (kChatStatusInactive, kChatStatusMute) or \
           status.permission == kChatPermissionInvalidUser:
          continue
        # different permission handler
        ensure_active_span = self.GetEnsureActiveSpanByPermission(status.permission)
        time_since_last_active = time.time() - status.last_active_time
        if time_since_last_active > ensure_active_span:
          # set in active
          await self.InactivateUser(status)
        else:
          # do forward
          command = ForwardCommand()
          command.task = get_result
          command.to_user_id = user_id
          await self._command_forward_queue.put(command)
          # await bot.copy_message(
          #   user_id,
          #   get_result.from_user_id, 
          #   get_result.from_message_id,
          #   caption="#message {}".format(get_result.task_index),
          #   disable_notification=True)
      # set current forward to true
      await self._from_message_db.SetSuccessForForwardTask(get_result)
      self._logger.info("done forward task #{} : {} - {} - {}".format(
          get_result.task_index, get_result.from_user_id, get_result.from_message_id, get_result.file_unique_id))

  async def SimpleForwardWorker(self):
    while True:
      get_item: ForwardCommand = await self._command_forward_queue.get()
      if get_item is None:
        break
      for try_cnt in range(5):
        try:
          await self._tg_app.bot.copy_message(
                get_item.to_user_id,
                get_item.task.from_user_id, 
                get_item.task.from_message_id,
                caption="#message {}".format(get_item.task.task_index),
                disable_notification=True)
          break
        except telegram.error.Forbidden as e:
          self._logger.info("forward message {} to {}, user is forbidden".format(get_item.task.task_index, get_item.to_user_id))
          user_st = self._user_status_dict.get(get_item.to_user_id, None)
          if user_st is not None:
            user_st.status = kChatStatusInactive
            user_st.permission = kChatPermissionGuestUser
            await self._user_status_db.UpdateUserPermission(get_item.to_user_id, user_st)
            await self._user_status_db.UpdateUserCurrentStatus(get_item.to_user_id, user_st)
          break
        except Exception as e:
          self._logger.info("(retry {}) forward message {} to {}, raised exception".format(
              try_cnt, get_item.task.task_index, get_item.to_user_id))
          self._logger.info("{}".format(e))
          await asyncio.sleep(5.0)  # wait 5 secs
        
        

  """ private function """
  async def AddNewUser(self, user_id):
    get_result = self._user_status_dict.get(user_id, None)
    if get_result is not None:
      return
    st = ChannelChatUserStatus()
    st.user_id = user_id
    await self._user_status_db.AddUserStatus(st)
    async with self._user_status_dict_access_lock:
      self._user_status_dict[user_id] = st

  async def ActivateOrSetActiveTime(self, status: ChannelChatUserStatus, update: telegram.Update=None):
    if status.status == kChatStatusInactive:
      await self.ActivateUser(status)
      if update is not None:
        await update.message.reply_text(f'user id: {update.effective_user.id}, activated')
    else:
      await self.DirectSetActiveTime(status)

  async def SetJoinTime(self, status: ChannelChatUserStatus):
    status.join_time = time.time()
    await self._user_status_db.UpdateUserJoinTime(status.user_id, status)

  async def DirectSetActiveTime(self, status: ChannelChatUserStatus):
    status.last_active_time = time.time()
    await self._user_status_db.UpdateUserLastActiveTime(status.user_id, status)

  async def ActivateUser(self, status: ChannelChatUserStatus):
    self._active_user_count += 1
    status.status = kChatStatusActive
    status.last_active_time = time.time()
    self._logger.info("user activated: {}".format(status.user_id))
    await self._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
    await self._user_status_db.UpdateUserLastActiveTime(status.user_id, status)
  
  async def InactivateUser(self, status: ChannelChatUserStatus):
    self._active_user_count -= 1
    status.status = kChatStatusInactive
    self._logger.info("user inactivated: {}".format(status.user_id))
    await self._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
    # notify
    bot: telegram.Bot = self._tg_app.bot
    try:
      await bot.send_message(status.user_id, "you have be inactive for a while, your active status is set to False, send a video or photo to reactivate")
    except Exception as e:
      self._logger.info("send inactive message to {} failed".format(status.user_id))

  def GetEnsureActiveSpanByPermission(self, permission):
    span = 0
    if permission == kChatPermissionGuestUser:
      span = 28800  # 8 hours
    elif permission == kChatPermissionNormalUser:
      span = 86400  # 12 hours
    elif permission == kChatPermissionVIPUser:
      span = 172800  # 24 hours
    elif permission == kChatPermissionAdminUser:
      span = 1e10
    return span


def BotChannelChatMain(bot_token, root_folder="workspace/bot_channel_chat"):
  LoggingAddFileHandler(root_folder + "/logs.txt")
  bcc = BotChannelChat(root_folder)

  app = telegram.ext.ApplicationBuilder().token(bot_token).build()
  bcc.PrepareHandlers(app)
  app.post_init = bcc.Initiate
  app.post_stop = bcc.PrepareStop

  app.run_polling()

async def ImportUsers(root_folder="workspace/bot_channel_chat"):
  bcc = BotChannelChat(root_folder)
  await bcc.Initiate(None)
  with open("workspace/xh_members.json", "r") as f:
    member_id_list = json.load(f)
  for member_id in member_id_list:
    await bcc.AddNewUser(member_id)
  bcc._user_status_db.Commit()

if __name__ == "__main__":
  # BotChannelChatMain("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo")
  # BotChannelChatMain("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo", "\\\\192.168.1.220\\home\\telegram_workspace\\bot_channel_chat")

  # asyncio.run(ImportUsers())

  with open("config/chat_bot_token.txt", "r") as f:
    token = f.read()
  # BotChannelChatMain(token)
  BotChannelChatMain(token, "\\\\192.168.1.220\\home\\telegram_workspace\\bot_channel_chat")