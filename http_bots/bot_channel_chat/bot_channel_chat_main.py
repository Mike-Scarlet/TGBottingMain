
"""
user info db
message process queue
"""

from python_general_lib.environment_setup.logging_setup import *
from python_general_lib.interface.json_serializable import *
from utils.async_single_db_auto_commit_serializable_object import *
from http_bots.bot_channel_chat.bot_channel_chat_constants import *
import telegram
import telegram.ext
import os

class ForwardTask:
  def __init__(self) -> None:
    self.from_user_id = None
    self.from_message_id = None
    self.file_unique_id = None
    # TODO

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

class FromMessagesManageDatabase(AsyncSingleDBAutoCommitSerializableObject):
  def __init__(self, db_path: str = None) -> None:
    super().__init__(db_path, from_messages_table_structure)

  async def Initiate(self, loop: asyncio.AbstractEventLoop):
    await super().Initiate(loop)

class BotChannelChat:
  def __init__(self, workspace_folder) -> None:
    self._logger = logging.getLogger("BotChannelChat")
    self._workspace_folder = workspace_folder
    self._from_message_db = None
    self._user_status_db = None
    self._user_status_dict = {}
    self._forward_process_queue = asyncio.Queue(100)  # max store 100 messages

  def PrepareHandlers(self, app: telegram.ext.Application):
    app.add_handler(telegram.ext.CommandHandler("start", self.StartHandler))
    app.add_handler(
      telegram.ext.MessageHandler(telegram.ext.filters.PHOTO | telegram.ext.filters.VIDEO, self.MediaHandler)
      )

  async def Initiate(self, app: telegram.ext.Application):
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
      self._user_status_dict[st.user_id] = st

    self._logger.info("initiate is finished")

  async def PrepareStop(self, app: telegram.ext.Application):
    # do all clean process here
    pass

  """ handlers """
  async def StartHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
      return
    await update.message.reply_text(f'Hello {update.effective_user.first_name}')

  async def MediaHandler(self, update: telegram.Update, context: telegram.ext.ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None:
      return
    if update.effective_message.video is not None:
      # add video
      pass
    if update.effective_message.photo is not None:
      valid_photo = update.effective_message.photo[-1]
      pass
    
    if not isinstance(attachment, (telegram.Video, telegram.ChatPhoto)):
      return
    update.effective_message.effective_attachment
    pass
    update.get_bot().forward_message()

  """ worker loop """
  async def ForwardWorkerLoop(self):
    pass
 
def BotChannelChatMain(bot_token):
  bcc = BotChannelChat("workspace/bot_channel_chat")

  app = telegram.ext.ApplicationBuilder().token(bot_token).build()
  bcc.PrepareHandlers(app)
  app.post_init = bcc.Initiate
  app.post_stop = bcc.PrepareStop

  app.run_polling()

if __name__ == "__main__":
  asyncio.run(BotChannelChatMain("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo"))