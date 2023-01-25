
from core.telegram_session_config import *
import pyrogram
import asyncio
import logging

class TelegramSession:
  def __init__(self, sess_config) -> None:
    param_dict = {
      "api_id": sess_config.api_id,
      "api_hash": sess_config.api_hash,
      "workdir": sess_config.work_dir,
    }
    self.client = pyrogram.Client(
      "telegram_local_bot",
      **param_dict
      # TODO: proxy
    )
    self.loop = asyncio.get_event_loop()
    self.logger = logging.getLogger("TelegramSession")

  def RunCoroutine(self, cor):
    return self.loop.run_until_complete(cor)

  def ScheduleCoroutine(self, cor):
    return self.loop.create_task(cor)

  def StartSession(self):
    """ start a telegram session, you must call this before using any other functions """
    async def StartClient(client: pyrogram.client):
      await client.start()
    self.logger.info("starting telegram session ...")
    self.RunCoroutine(StartClient(self.client))
    self.logger.info("telegram session started.")
  
  def ListAllDialogs(self):
    """ a helpful function to get all dialogs and their id """
    async def GetAllDialogsInternal(client: pyrogram.client):
      async for dialog in client.get_dialogs():
        chat_name = dialog.chat.first_name or dialog.chat.title
        chat_id = dialog.chat.id
        print("{}: {}".format(chat_name, chat_id))
    self.logger.info("retrieving dialogs ...")
    self.RunCoroutine(GetAllDialogsInternal(self.client))

  async def StartSessionAsync(self):
    """ start a telegram session, you must call this before using any other functions """
    self.logger.info("starting telegram session ...")
    await self.client.start()
    self.logger.info("telegram session started.")

  async def ListAllDialogsAsync(self):
    """ a helpful function to get all dialogs and their id """
    self.logger.info("retrieving dialogs ...")
    async for dialog in self.client.get_dialogs():
      chat_name = dialog.chat.first_name or dialog.chat.title
      chat_id = dialog.chat.id
      print("{}: {}".format(chat_name, chat_id))

  async def GetAllDialogsAsync(self, limit=1e30) -> typing.List[typing.Tuple[str, pyrogram.types.Dialog]]:
    """ a helpful function to get all dialogs and their id """
    self.logger.info("retrieving all dialogs ...")
    result = []
    async for dialog in self.client.get_dialogs():
      chat_name = dialog.chat.first_name or dialog.chat.title
      result.append([chat_name, dialog])
      if len(result) >= limit:
        break
    return result

  async def GetAllDialogNameWithID(self):
    result = []
    async for dialog in self.client.get_dialogs():
      chat_name = dialog.chat.first_name or dialog.chat.title
      chat_id = dialog.chat.id
      result.append([chat_name, chat_id])
    return result