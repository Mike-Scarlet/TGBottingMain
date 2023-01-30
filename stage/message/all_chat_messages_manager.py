
import typing
from core.telegram_session import *
from stage.message.single_chat_message_manager import *
import os
import logging

HistoryRetriveModes = [
  kHistoryRetrieveFromBegin,
  kHistoryRetrieveFromLastMessage,
] = range(2)

class MessageCallbackPack:
  message: pyrogram.types.Message
  message_dict: dict

  def __init__(self) -> None:
    self.message = None
    self.message_dict = None

class AllChatMessageManager:
  _chat_id_message_manager_dict: typing.Dict[int, SingleChatMessageManager]

  def __init__(self, telegram_session: TelegramSession, all_chat_db_store_folder: str) -> None:
    self._telegram_session = telegram_session
    self._all_chat_db_store_folder = all_chat_db_store_folder
    if not os.path.exists(self._all_chat_db_store_folder):
      os.makedirs(self._all_chat_db_store_folder)
    self._chat_id_message_manager_dict = {}
    self._chat_id_message_manager_dict_access_lock = asyncio.Lock()

    # for callback process
    self._callback_queue_access_lock = asyncio.Lock()
    self._callback_queue = asyncio.Queue(200)

    #
    self.logger = logging.getLogger("AllChatMessageManager")

  def GetCallbackQueue(self):
    return self._callback_queue

  async def StopTrackChatManager(self, chat_id):
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
      if get_result is not None:
        get_result.Commit()
        del self._chat_id_message_manager_dict[chat_id]

  async def GeneralHistoryRetrieve(self, chat_id, history_retrieve_mode=kHistoryRetrieveFromLastMessage):
    # must process from begin
    self.logger.info("> call GeneralHistoryRetrieve for {}, mode = {}".format(chat_id, history_retrieve_mode))
    chat_manager = await self._GetOrCreateChatManager(chat_id)
    next_chat_retrieve_begin_message_id = 0
    if history_retrieve_mode == kHistoryRetrieveFromLastMessage:
      # need to get max message id from chat manager
      next_chat_retrieve_begin_message_id = chat_manager.GetLastMessageID() + 1
    self.logger.info(" - GeneralHistoryRetrieve for {}, start from message: {}".format(chat_id, next_chat_retrieve_begin_message_id))
    await self._AddChatManager(chat_manager)
    await self._ChatAllHistoryHandler(chat_manager, next_chat_retrieve_begin_message_id)
    self.logger.info("< done GeneralHistoryRetrieve for {}, mode = {}, last message is {}".format(chat_id, history_retrieve_mode, chat_manager.GetLastMessageID()))

  async def CallbackMessageHandler(self, client, message: pyrogram.types.Message):
    # the handler for all callback message
    chat_id = message.chat.id
    get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is not None:
      await self._GeneralInsertMessage(get_result, message, kChatMessageSourceFromReceive)

  """ private functions """
  """ >> chat manager adjustment """
  async def _GetOrCreateChatManager(self, chat_id) -> SingleChatMessageManager:
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is None:
      get_result = SingleChatMessageManager(
        chat_id,
        os.path.join(self._all_chat_db_store_folder, "{}.db".format(chat_id)))
      await get_result.InitiateDB()
      await get_result.InitiateMessageIDSet()
      await get_result.InitiateFileUniqueIDSet()
    return get_result

  async def _AddChatManager(self, single_chat_manager: SingleChatMessageManager):
    async with self._chat_id_message_manager_dict_access_lock:
      if single_chat_manager.GetChatID() not in self._chat_id_message_manager_dict:
        self._chat_id_message_manager_dict[single_chat_manager.GetChatID()] = single_chat_manager
      else:
        pass

  """ >> messages handler """
  async def _ChatAllHistoryHandler(self, chat_manager: SingleChatMessageManager, from_message_id: int):
    history_gen = self._telegram_session.client.get_chat_history(
        chat_id=chat_manager.GetChatID(), 
        offset_id=from_message_id,
        reverse=True)
    async for message in history_gen:
      await self._GeneralInsertMessage(chat_manager, message, kChatMessageSourceFromHistory)
    # commit if all history is resolved
    await chat_manager.Commit()

  async def _ManualMessageDispatch(self, manual_message: pyrogram.types.Message):
    chat_id = manual_message.chat.id
    get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is not None:
      await self._GeneralInsertMessage(get_result, manual_message, kChatMessageSourceFromManual)

  async def _MessageInserted(self, pack: MessageCallbackPack):
    async with self._callback_queue_access_lock:
      await self._callback_queue.put(pack)

  async def _GeneralInsertMessage(self, chat_manager: SingleChatMessageManager, message: pyrogram.types.Message, message_source: "ChatMessageSource"):
    insert_dict = await chat_manager.InsertMessage(message, message_source)
    pack = self._PackAsMessageCallbackPack(message, insert_dict)
    await self._MessageInserted(pack)

  def _PackAsMessageCallbackPack(self, message, message_dict):
    result = MessageCallbackPack()
    result.message = message
    result.message_dict = message_dict
    return result