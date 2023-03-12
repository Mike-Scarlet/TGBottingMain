
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
from http_bots.bot_channel_chat.bot_channel_chat_sub_databases import *
from utils.command_parser import ParsedCommand
from utils.telegram_asyncio_helper import TGFuncWrap
import names
import telegram
import telegram.ext
import os, time, datetime
import collections

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
    self._active_user_count = 0

    # auto add user
    self._auto_add_user = False

    self._ban_messages_access_lock = asyncio.Lock()
    self._ban_messages = set()

    # workers
    self._forward_worker_task = None

    self._command_forward_worker_count = 50
    self._command_forward_workers = []
    self._command_forward_queue = asyncio.Queue(1)

    self._command_forward_collect_task = None
    self._command_forwarded_collect_queue = asyncio.Queue(self._command_forward_worker_count)

  def PrepareHandlers(self, app: telegram.ext.Application):
    # command handler
    self._general_user_commands_desc_cb_level_list = [
      ["start", "start the bot", self.StartHandler],
      ["help", "get help info", self.HelpHandler],
      ["join", "join the chat and activate your status", self.JoinHandler],
      ["current_status", "get your current status", self.CurrentStatusHandler],
      ["get_chat_status", "get the active member of the chat and check if the bot is valid", self.GetChatStatusHandler],
    ]
    self._administrative_commands_desc_cb_level_list = [
      ["add_user", "add user by user id", self.AddUserHandler],
      ["get_user_status", "get user status by user id", self.GetUserStatusHandler],
      ["set_user_status", "set user status by user id", self.SetUserStatusHandler],
      ["punish_user_by_message_id", "punish user status by message id", self.PunishUserByMessageID],
      ["ban_user_by_message_id", "ban user status by message id", self.BanUserByMessageID],
      ["get_message_info", "get message info by message id", self.GetMessageInfoHandler],
      ["extra_process_function", "abstract extra process function", self.ExtraProcessFunctionHandler],
    ]
    command_handler_grps = [self._general_user_commands_desc_cb_level_list, self._administrative_commands_desc_cb_level_list]
    for handler_grp in command_handler_grps:
      for handler in handler_grp:
        app.add_handler(telegram.ext.CommandHandler(handler[0], handler[2]))

    # media handler
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
      # history data complement
      if st.active_expire_time == 0 or st.active_expire_time is None:
        st.active_expire_time = st.last_active_time + self.GetMinimumSecondsIntervalByPermission(st.permission) * 2
        await self._user_status_db.UpdateUserLastActiveAndExpireTime(st.user_id, st)
      if st.fake_name is None:
        self.AutoSetNameForStatus(st)
        await self._user_status_db.UpdateUserFakeName(st.user_id, st)

    # all worker create
    self._forward_worker_task = loop.create_task(self.ForwardWorkerLoop())
    for _ in range(self._command_forward_worker_count):
      self._command_forward_workers.append(loop.create_task(self.SimpleForwardWorker()))
    self._command_forward_collect_task = loop.create_task(self.ForwardResultCollector())

    self._logger.info("initiate is finished")
    self._logger.info("start to handle histories")
    fail_tasks = await self._from_message_db.GetFailForwardTasks()
    for forward_task in fail_tasks:
      # try get from user name
      try:
        user_st = self._user_status_dict.get(forward_task.from_user_id)
        forward_task.from_fake_name = user_st.fake_name
      except:
        pass
      self._logger.info("add history forward task #{} : {} - {} - {}".format(
        forward_task.task_index, forward_task.from_user_id, forward_task.from_message_id, forward_task.file_unique_id))
      await self._forward_process_queue.put(forward_task)
    self._logger.info("history handle finished")

  async def PrepareStop(self, app: telegram.ext.Application):
    # do all clean process here
    pass

  """ handlers """
  async def StartHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = self.GetUserFromUpdate(update)
    if user is None:
      return
    await self.ReplyText(update, "Hello {}, your user id is {}, send /join to join the chat, send /current_status to check your status".format(user.first_name, user.id))

  async def JoinHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    if self._auto_add_user:
      user_st = await self.GetOrCreateUserStatusFromUpdate(update)
    else:
      user_st = self.GetUserStatusFromUpdate(update)
    if user_st is None:
      self._logger.info("inrecognized user {} - {} sent join".format(user.id, user.full_name))
      await self.ReplyText(update, 'bot error, please contact admin')
      return
    if user_st.join_time == 0:
      await self.SetJoinTime(user_st)
      await self.SendHelpToUser(user_st)
    if user_st.permission not in (kChatPermissionInvalidUser,):
      await self.UpdateExpireTimeAndActivate(user_st, update, user_active_expire_offset=0)
    else:
      await self.ReplyText(update, 'sorry but you do not have permission')

  async def CurrentStatusHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetUserStatusFromUpdate(update)
    if user_st is None:
      await self.ReplyText(update, "you haven't joined yet")
    else:
      await self.ReplyText(update, self.UserStatusToInfoString(user_st))

  async def HelpHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetUserStatusFromUpdate(update)
    if user_st is None:
      return
    await self.SendHelpToUser(user_st)

  async def GetChatStatusHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetUserStatusFromUpdate(update)
    await self.ReplyText(update, 'the process queue size is {}, the active user count is {}'.format(self._forward_process_queue.qsize(), self._active_user_count))

  async def AddUserHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    # parse user id
    try:
      user_id = int(update.effective_message.text.replace("/add_user ", ""))
      if user_id in self._user_status_dict:
        await self.ReplyText(update, 'user already exists: {}'.format(user_id))
        return
      else:
        await self.AddNewUser(user_id)
    except:
      await self.ReplyText(update, 'fail to add user: "{}"'.format(update.effective_message.text))
      return
    await self.ReplyText(update, 'user added: {}'.format(user_id))
    self._logger.info("admin {} added user: {}".format(user_st.user_id, user_id))

  async def GetUserStatusHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    try:
      parsed_command = ParsedCommand()
      parsed_command.ParseCommand(update.effective_message.text)
      user_id = parsed_command.GetIntParam(0)
      if user_id is None:
        raise ValueError("parse param error")
      get_result = self._user_status_dict.get(user_id, None)
      if get_result is None:
        await update.message.reply_text("cannot find user {}".format(user_id))
        return
      obj_dict = AutoObjectToJsonHandler(get_result)
      await update.message.reply_text(json.dumps(obj_dict, indent=2))
    except Exception as e:
      await self.ReplyError(update, "GetUserStatusHandler", exception=e)

  async def SetUserStatusHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    try:
      parsed_command = ParsedCommand()
      parsed_command.ParseCommand(update.effective_message.text)
      user_id = parsed_command.GetIntParam(0)
      permission_value = parsed_command.GetIntParam(1)
      status_value = parsed_command.GetIntParam(2)
      if user_id is None:
        raise ValueError("parse param user id error")
      get_result = self._user_status_dict.get(user_id, None)
      if get_result is None:
        await update.message.reply_text("cannot find user {}".format(user_id))
        return
      if permission_value is not None:
        get_result.permission = permission_value
        await update.message.reply_text("user {} set permission to {}".format(user_id, permission_value))
      if status_value is not None:
        get_result.status = status_value
        await update.message.reply_text("user {} set status to {}".format(user_id, status_value))
      await self._user_status_db.UpdateUserPermission(user_id, get_result)
      await self._user_status_db.UpdateUserCurrentStatus(user_id, get_result)
    except Exception as e:
      await self.ReplyError(update, "SetUserStatusHandler", exception=e)

  async def PunishUserByMessageID(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    try:
      parsed_command = ParsedCommand()
      parsed_command.ParseCommand(update.effective_message.text)
      message_index = parsed_command.GetIntParam(0)
      if message_index is None:
        raise ValueError("parse param message_index error")
      query_result = await self._from_message_db.GetForwardTaskByTaskIndex(message_index)
      if len(query_result) != 1:
        raise ValueError("PunishUserByMessageID query_result count is not 1: {}".format(query_result))
      queried_user_id = query_result[0]["from_user_id"]
      queried_user_st = self._user_status_dict.get(queried_user_id, None)
      if queried_user_st is None:
        raise ValueError("queried_user_st is None")
      await self.PunishUser(queried_user_st, message_index)
      await update.message.reply_text("done punish {}\n".format(queried_user_id) + json.dumps(query_result, indent=2))
    except Exception as e:
      await self.ReplyError(update, "PunishUserByMessageID", exception=e)

  async def BanUserByMessageID(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    try:
      parsed_command = ParsedCommand()
      parsed_command.ParseCommand(update.effective_message.text)
      message_index = parsed_command.GetIntParam(0)
      if message_index is None:
        raise ValueError("parse param message_index error")
      query_result = await self._from_message_db.GetForwardTaskByTaskIndex(message_index)
      if len(query_result) != 1:
        raise ValueError("BanUserByMessageID query_result count is not 1: {}".format(query_result))
      queried_user_id = query_result[0]["from_user_id"]
      queried_user_st = self._user_status_dict.get(queried_user_id, None)
      if queried_user_st is None:
        raise ValueError("queried_user_st is None")
      await self.BanUser(queried_user_st, message_index)
      await update.message.reply_text("done ban {}\n".format(queried_user_id) + json.dumps(query_result, indent=2))
    except Exception as e:
      await self.ReplyError(update, "BanUserByMessageID", exception=e)

  async def GetMessageInfoHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    try:
      parsed_command = ParsedCommand()
      parsed_command.ParseCommand(update.effective_message.text)
      message_index = parsed_command.GetIntParam(0)
      if message_index is None:
        raise ValueError("parse param message_index error")
      query_result = await self._from_message_db.GetForwardTaskByTaskIndex(message_index)
      await update.message.reply_text(json.dumps(query_result, indent=2))
    except Exception as e:
      await self.ReplyError(update, "SetUserStatusHandler", exception=e)

  async def ExtraProcessFunctionHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user_st = self.GetAdminUserStatusFromUpdate(update)
    if user_st is None:
      return
    try:
      parsed_command = ParsedCommand()
      parsed_command.ParseCommand(update.effective_message.text)
      command_name = parsed_command.GetStringParam(0)
      if command_name == "set_my_command_menu":
        command_str_pairs = []
        for l in self._general_user_commands_desc_cb_level_list:
          command_str_pairs.append((l[0], l[1]))
        for l in self._administrative_commands_desc_cb_level_list:
          command_str_pairs.append((l[0], l[1]))
        await self._tg_app.bot.set_my_commands(command_str_pairs, telegram.BotCommandScopeChat(user_st.user_id))
      elif command_name == "set_global_command_menu":
        command_str_pairs = []
        for l in self._general_user_commands_desc_cb_level_list:
          command_str_pairs.append((l[0], l[1]))
        # bot: telegram.Bot = None
        # bot.set_my_commands()
        await self._tg_app.bot.set_chat_menu_button(chat_id=None, menu_button=telegram.MenuButtonCommands())
        await self._tg_app.bot.set_my_commands(command_str_pairs, telegram.BotCommandScopeDefault())
      elif command_name == "broadcast_help":
        for uid, status in self._user_status_dict.items():
          if status.join_time > 1e7 or status.last_active_time > 1e7:
            await self.SendHelpToUser(status)
      else:
        raise ValueError("unrecognized command: {}".format(command_name))
      await update.message.reply_text("handle command {} done".format(command_name))
    except Exception as e:
      await self.ReplyError(update, "ExtraProcessFunctionHandler", exception=e)

  async def MediaHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None:
      return
    
    # current we only accept exist users
    user_st = self._user_status_dict.get(update.effective_chat.id, None)
    if user_st is None:
      return
    
    # TODO: global status check
    # update user current status
    has_video = update.effective_message.video is not None
    has_photo = update.effective_message.photo is not None and len(update.effective_message.photo) > 0

    if has_video or has_photo:
      if user_st.permission == kChatPermissionInvalidUser:
        return

      if has_video:
        await self.UpdateExpireTimeAndActivate(user_st, update, 9000)  # 2.5 hours
      elif has_photo:
        await self.UpdateExpireTimeAndActivate(user_st, update, 3600)  # 1 hour
    forward_task = None
    if has_video:
      # add video
      forward_task = ForwardTask()
      forward_task.from_user_id = update.effective_chat.id
      forward_task.from_message_id = update.effective_message.message_id
      forward_task.from_fake_name = user_st.fake_name
      forward_task.file_unique_id = update.effective_message.video.file_unique_id
      # add to status store db
      await self._from_message_db.AddForwardTask(forward_task)
      await self._forward_process_queue.put(forward_task)
    if has_photo:
      valid_photo = update.effective_message.photo[-1]
      forward_task = ForwardTask()
      forward_task.from_user_id = update.effective_chat.id
      forward_task.from_message_id = update.effective_message.message_id
      forward_task.from_fake_name = user_st.fake_name
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
      
      # collect need to add forward tasks, get this task total forward count
      valid_user_ids = []
      for user_id, status in user_status_list:
        # TODO: mute handle here is bad
        if status.status in (kChatStatusInactive, kChatStatusMute) or \
           status.permission == kChatPermissionInvalidUser:
          continue
        # different permission handler
        if time.time() > status.active_expire_time:
          # set in active
          await self.InactivateUser(status)
        else:
          # collect the user id
          valid_user_ids.append(user_id)

      # construct forward command
      get_result.total_need_to_forward_count = len(valid_user_ids)
      for uid in valid_user_ids:
        # do forward
        command = ForwardCommand()
        command.task = get_result
        command.to_user_id = uid
        await self._command_forward_queue.put(command)
      
      # set current forward to true
      # await self._from_message_db.SetSuccessForForwardTask(get_result)
      self._logger.info("done feed forward task #{} : {} - {} - {}".format(
          get_result.task_index, get_result.from_user_id, get_result.from_message_id, get_result.file_unique_id))

  async def SimpleForwardWorker(self):
    while True:
      get_item: ForwardCommand = await self._command_forward_queue.get()
      if get_item is None:
        break
      for try_cnt in range(5):
        if get_item.task.task_index in self._ban_messages:
          get_item.user_forward_status = kUserForwardStatusFailDueToInvalidSource
          break   # early stop
        try:
          await self._tg_app.bot.copy_message(
                get_item.to_user_id,
                get_item.task.from_user_id, 
                get_item.task.from_message_id,
                caption="#message {}\nfrom #{}".format(get_item.task.task_index, get_item.task.from_fake_name),
                disable_notification=True)
          get_item.user_forward_status = kUserForwardStatusSuccess
          break
        except telegram.error.Forbidden as e:
          # in this case, we handle situation where user block the bot
          self._logger.info("forward message {} to {}, user is forbidden".format(get_item.task.task_index, get_item.to_user_id))
          user_st = self._user_status_dict.get(get_item.to_user_id, None)
          if user_st is not None:
            user_st.status = kChatStatusInactive
            user_st.permission = kChatPermissionGuestUser
            await self._user_status_db.UpdateUserPermission(get_item.to_user_id, user_st)
            await self._user_status_db.UpdateUserCurrentStatus(get_item.to_user_id, user_st)
          get_item.user_forward_status = kUserForwardStatusFailDueToInvalidUser
          break
        except (telegram.error.NetworkError, telegram.error.TimedOut) as e:
          # in this case, we handle situation where the connection fails
          if isinstance(e, telegram.error.BadRequest) and e.message == "Message to copy not found":
            async with self._ban_messages_access_lock:
              self._ban_messages.add(get_item.task.task_index)
            get_item.user_forward_status = kUserForwardStatusFailDueToInvalidSource
            break
          get_item.user_forward_status = kUserForwardStatusFailDueToNetworkIssue
          # self._logger.info("(retry {}) forward message {} to {}, raised network error {} - {}".format(
          #     try_cnt, get_item.task.task_index, get_item.to_user_id, type(e), e))
          await asyncio.sleep(5.0)  # wait 5 secs
        except telegram.error.RetryAfter as e:
          await asyncio.sleep(e.retry_after + 2.0)
        except Exception as e:
          get_item.user_forward_status = kUserForwardStatusFailReasonUnrecognized
          if e.message == "Chat not found":
            try:
              target_user_st = self._user_status_dict[get_item.to_user_id]
              await self.InactivateUser(target_user_st)
            except:
              pass
            break
          self._logger.info("forward message {} to {}, raised unrecognized exception".format(
              get_item.task.task_index, get_item.to_user_id))
          self._logger.info("{} - {}".format(type(e), e))
          break
      await self._command_forwarded_collect_queue.put(get_item)

  async def ForwardResultCollector(self):
    # to judge a forward status
    task_id_forward_commands_list_dict: typing.Dict[int, typing.List[ForwardCommand]]
    task_id_forward_commands_list_dict = collections.defaultdict(list)
    while True:
      get_item: ForwardCommand = await self._command_forwarded_collect_queue.get()
      if get_item is None:
        break
      current_list = task_id_forward_commands_list_dict[get_item.task.task_index]
      current_list.append(get_item)
      if current_list[0].task.total_need_to_forward_count > len(current_list):
        continue  # no further process
      # judge the forward status
      fail_counter = 0
      invalid_counter = 0
      for command in current_list:
        if command.user_forward_status in (kUserForwardStatusUnknown, 
                                           kUserForwardStatusFailDueToNetworkIssue, 
                                           kUserForwardStatusFailReasonUnrecognized):
          fail_counter += 1
        elif command.user_forward_status == kUserForwardStatusFailDueToInvalidSource:
          invalid_counter += 1
      if invalid_counter > 0:
        judged_status = kForwardStatusInvalid
        await self._from_message_db.SetInvalidForForwardTask(get_item.task)
        try:
          async with self._ban_messages_access_lock:
            self._ban_messages.remove(get_item.task.task_index)
        except:
          pass
      elif fail_counter >= 10:
        judged_status = kForwardStatusInQueue
      else:
        judged_status = kUserForwardStatusSuccess
        await self._from_message_db.SetSuccessForForwardTask(get_item.task)
      forward_task = get_item.task
      self._logger.info("forward status is set to {} for task #{} : {} - {} - {}".format(
          judged_status,
          forward_task.task_index, forward_task.from_user_id, 
          forward_task.from_message_id, forward_task.file_unique_id))
      # remove this collection
      del task_id_forward_commands_list_dict[get_item.task.task_index]

  """ private function """
  def DoesUserHasAdminRight(self, user_st: ChannelChatUserStatus):
    try:
      if user_st is None:
        return False
      if user_st.permission < kChatPermissionAdminUser:
        return False
      return True
    except Exception as e:
      self._logger.warning("error in DoesUserHasAdminRight: {} - {}", type(e), e)
      return False

  def UserStatusToInfoString(self, user_st: ChannelChatUserStatus):
    st = "your user id: {}\nyour display name: {}\nyour active status: {}".format(user_st.user_id, user_st.fake_name, user_st.status != kChatStatusInactive)
    if user_st.status != kChatStatusInactive:
      seconds_diff = user_st.active_expire_time - time.time()
      if seconds_diff > 0:
        days = round(seconds_diff // 86400)
        hours = round((seconds_diff % 86400) // 3600)
        minutes = round((seconds_diff % 3600) // 60)
        st += "\nyour active status expires in:\n  {} day(s) {} hour(s) {} minute(s)".format(days, hours, minutes)
    return st

  def GetMinimumSecondsIntervalByPermission(self, permission):
    return minimum_seconds_interval_by_permission.get(permission, 0)

  def GetMaximumSecondsIntervalByPermission(self, permission):
    return maximum_seconds_interval_by_permission.get(permission, 0)

  def GetUserFromUpdate(self, update: telegram.Update):
    return update.effective_user

  async def GetOrCreateUserStatusFromUpdate(self, update: telegram.Update):
    try:
      user_st = self._user_status_dict.get(update.effective_user.id, None)
      if user_st is None:
        # create one
        await self.AddNewUser(update.effective_user.id)
        user_st = self._user_status_dict.get(update.effective_user.id, None)
      return user_st
    except:
      return None

  def GetUserStatusFromUpdate(self, update: telegram.Update):
    try:
      user_st = self._user_status_dict.get(update.effective_user.id, None)
      return user_st
    except:
      return None

  def GetAdminUserStatusFromUpdate(self, update: telegram.Update):
    try:
      user_st = self._user_status_dict.get(update.effective_user.id, None)
      if self.DoesUserHasAdminRight(user_st):
        return user_st
      return None
    except:
      return None

  async def ReplyText(self, update: telegram.Update, *args, **kwargs):
    async def ReplyImpl(update: telegram.Update, *args, **kwargs):
      return await update.message.reply_text(*args, **kwargs)
    await TGFuncWrap(ReplyImpl(update, *args, **kwargs))

  async def RawUpdateUserActiveAndExpireTimeByNow(self, status: ChannelChatUserStatus, min_interval_value, max_interval_value, expire_time_offset=0):
    status.last_active_time = time.time()
    # update expire time
    min_expire_time = min_interval_value + status.last_active_time
    max_expire_time = max_interval_value + status.last_active_time

    if status.active_expire_time < min_expire_time:
      status.active_expire_time = min_expire_time
    status.active_expire_time += expire_time_offset
    if status.active_expire_time > max_expire_time:
      status.active_expire_time = max_expire_time

    await self._user_status_db.UpdateUserLastActiveAndExpireTime(status.user_id, status)

  async def UpdateUserActiveAndExpireTimeByDefaultPermissionByNow(self, status: ChannelChatUserStatus, expire_time_offset=0):
    await self.RawUpdateUserActiveAndExpireTimeByNow(
      status,
      self.GetMinimumSecondsIntervalByPermission(status.permission), 
      self.GetMaximumSecondsIntervalByPermission(status.permission),
      expire_time_offset
    )

  async def ReplyError(self, update: telegram.Update, entry_name="", exception=None):
    try:
      await update.message.reply_text('[{}] argument error: "{}"'.format(entry_name, update.effective_message.text))
      if exception is not None:
        await update.message.reply_text("{}".format(exception))
    except Exception as e:
      pass

  async def AddNewUser(self, user_id, permission=kChatPermissionNormalUser):
    get_result = self._user_status_dict.get(user_id, None)
    if get_result is not None:
      return
    st = ChannelChatUserStatus()
    st.permission = permission
    st.user_id = user_id
    self.AutoSetNameForStatus(st)
    await self._user_status_db.AddUserStatus(st)
    async with self._user_status_dict_access_lock:
      self._user_status_dict[user_id] = st

  async def UpdateExpireTimeAndActivate(self, status: ChannelChatUserStatus, update: telegram.Update=None, user_active_expire_offset=0):
    # expire time
    await self.UpdateUserActiveAndExpireTimeByDefaultPermissionByNow(status, user_active_expire_offset)
    if status.status == kChatStatusInactive:
      # also do activate
      await self.ActivateUser(status)
      if update is not None:
        await self.ReplyText(update, 'user id: {}, activated'.format(update.effective_user.id))

  def AutoSetNameForStatus(self, status: ChannelChatUserStatus):
    if status.fake_name is not None:
      return
    
    exist_names = set(map(lambda x: x.fake_name, self._user_status_dict.values()))
    for _ in range(10):
      name = names.get_last_name()
      if name in exist_names:
        continue
      else:
        break
    status.fake_name = name

  async def SetJoinTime(self, status: ChannelChatUserStatus):
    status.join_time = time.time()
    await self._user_status_db.UpdateUserJoinTime(status.user_id, status)

  async def ActivateUser(self, status: ChannelChatUserStatus):
    self._active_user_count += 1
    status.status = kChatStatusActive
    self._logger.info("user activated: {}".format(status.user_id))
    await self._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
  
  async def InactivateUser(self, status: ChannelChatUserStatus):
    self._active_user_count -= 1
    status.status = kChatStatusInactive
    self._logger.info("user inactivated: {}".format(status.user_id))
    await self._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
    # notify
    bot: telegram.Bot = self._tg_app.bot
    try:
      await bot.send_message(status.user_id, "you have been inactive for a while, your active status is set to False, send a video or photo or /join to reactivate")
    except Exception as e:
      self._logger.info("send inactive message to {} failed".format(status.user_id))

  async def PunishUser(self, status: ChannelChatUserStatus, source_message_index):
    self._active_user_count -= 1
    status.status = kChatStatusInactive
    status.active_expire_time = time.time()
    self._logger.info("user punished: {}".format(status.user_id))
    await self._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
    await self._user_status_db.UpdateUserLastActiveAndExpireTime(status.user_id, status)
    # notify
    bot: telegram.Bot = self._tg_app.bot
    try:
      await self.SendHelpToUser(status)
      await bot.send_message(status.user_id, "you are punished by #message {}, now your active status is False".format(source_message_index))
    except Exception as e:
      self._logger.info("send punish message to {} failed".format(status.user_id))

  async def BanUser(self, status: ChannelChatUserStatus, source_message_index):
    self._active_user_count -= 1
    status.status = kChatStatusInactive
    status.permission = kChatPermissionInvalidUser
    self._logger.info("user banned: {}".format(status.user_id))
    await self._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
    await self._user_status_db.UpdateUserPermission(status.user_id, status)
    # notify
    bot: telegram.Bot = self._tg_app.bot
    try:
      await self.SendHelpToUser(status)
      await bot.send_message(status.user_id, "you are banned by #message {}, thanks for your contribution".format(source_message_index))
    except Exception as e:
      self._logger.info("send ban message to {} failed".format(status.user_id))

  async def SendHelpToUser(self, status: ChannelChatUserStatus):
    bot: telegram.Bot = self._tg_app.bot
    min_hours = self.GetMinimumSecondsIntervalByPermission(status.permission) // 3600
    max_hours = self.GetMaximumSecondsIntervalByPermission(status.permission) // 3600
    for _ in range(3):
      try:
        await bot.send_message(status.user_id, bot_help_info_str.format(min_hours, max_hours))
        break
      except Exception as e:
        self._logger.info("send help message to {} failed - {} {}".format(status.user_id, type(e), e))
        await asyncio.sleep(1)

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

async def RemapPermissions(root_folder="workspace/bot_channel_chat"):
  raise ValueError()
  bcc = BotChannelChat(root_folder)
  await bcc.Initiate(None)

  permission_map = {
    0: kChatPermissionInvalidUser,
    1: kChatPermissionAdminUser,
    2: kChatPermissionVIPUser,
    3: kChatPermissionNormalUser,
    4: kChatPermissionGuestUser
  }
 
  for uid, status in bcc._user_status_dict.items():
    status.permission = permission_map[status.permission]
    await bcc._user_status_db.UpdateUserPermission(uid, status)
  bcc._user_status_db.Commit()

async def RefreshActiveTime(root_folder="workspace/bot_channel_chat"):
  bcc = BotChannelChat(root_folder)
  await bcc.Initiate(None)

  current_time = time.time()
  for uid, status in bcc._user_status_dict.items():
    if status.join_time > 1e7 or status.last_active_time > 1e7:
      time_diff = status.active_expire_time - status.last_active_time
      status.active_expire_time = current_time
      await bcc.RawUpdateUserActiveAndExpireTimeByNow(
        status, 
        bcc.GetMinimumSecondsIntervalByPermission(status.permission), 
        bcc.GetMaximumSecondsIntervalByPermission(status.permission),
        time_diff)
      status.status = kChatStatusActive
      await bcc._user_status_db.UpdateUserCurrentStatus(status.user_id, status)
  bcc._user_status_db.Commit()

if __name__ == "__main__":
  # BotChannelChatMain("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo")
  # BotChannelChatMain("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo", "\\\\192.168.1.220\\home\\telegram_workspace\\bot_channel_chat")

  # asyncio.run(RefreshActiveTime())

  # asyncio.run(ImportUsers())
  # telegram.ext.Application

  with open("config/chat_bot_token.txt", "r") as f:
    token = f.read()
  # BotChannelChatMain(token)
  BotChannelChatMain(token, "\\\\192.168.1.220\\home\\telegram_workspace\\bot_channel_chat")