
"""
user info db
message process queue
"""

from python_general_lib.environment_setup.logging_setup import *
from utils.async_single_db_auto_commit_serializable_object import *
from http_bots.bot_channel_chat.bot_channel_chat_constants import *
import telegram
import telegram.ext

class ChannelChatUserStatus:
  def __init__(self) -> None:
    self.permission = kChatPermissionInvalidUser
    self.status = kChatStatusInactive
    self.last_active_time = 0

class FromMessagesManageDatabase(AsyncSingleDBAutoCommitSerializableObject):
  def __init__(self, db_path: str = None) -> None:
    super().__init__(db_path, from_messages_table_structure)

  async def Initiate(self, loop: asyncio.AbstractEventLoop):
    await super().Initiate(loop)

class BotChannelChat:
  def __init__(self) -> None:
    self._logger = logging.getLogger("BotChannelChat")

  def PrepareHandlers(self, app: telegram.ext.Application):
    app.add_handler(telegram.ext.CommandHandler("start", self.StartHandler))
    app.add_handler(
      telegram.ext.MessageHandler(None, self.MessagesHandler)
      )

  async def Initiate(self, app: telegram.ext.Application):
    # do all initiate process here
    self._logger.info("initiate is called")
    loop = asyncio.get_event_loop()
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

  async def MessagesHandler(self, *args, **kwargs):
    pass
  
def BotChannelChatMain(bot_token):
  bcc = BotChannelChat()

  app = telegram.ext.ApplicationBuilder().token(bot_token).build()
  bcc.PrepareHandlers(app)
  app.post_init = bcc.Initiate
  app.post_stop = bcc.PrepareStop

  app.run_polling()

if __name__ == "__main__":
  asyncio.run(BotChannelChatMain("6141949745:AAEcQUrzmnWuDxdpwjJa52IJeiTK9F9vKVo"))