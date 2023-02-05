
import typing
from core.telegram_session import *
from stage.message.single_chat_message_manager import *
import os
import logging
import math
import pyrogram.errors

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

  async def GetSingleChatManager(self, chat_id) -> typing.Optional[SingleChatMessageManager]:
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    return get_result

  async def StopTrackChatManager(self, chat_id):
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
      if get_result is not None:
        get_result.Commit()
        del self._chat_id_message_manager_dict[chat_id]

  async def GeneralHistoryRetrieve(self, chat_id, history_retrieve_mode=kHistoryRetrieveFromLastMessage, force_update_db=False):
    # must process from begin
    self.logger.info("> call GeneralHistoryRetrieve for {}, mode = {}".format(chat_id, history_retrieve_mode))
    chat_manager = await self._GetOrCreateChatManager(chat_id)
    next_chat_retrieve_begin_message_id = 0
    if history_retrieve_mode == kHistoryRetrieveFromLastMessage:
      # need to get max message id from chat manager
      next_chat_retrieve_begin_message_id = chat_manager.GetLastMessageID() + 1
    self.logger.info(" - GeneralHistoryRetrieve for {}, start from message: {}".format(chat_id, next_chat_retrieve_begin_message_id))
    await self._AddChatManager(chat_manager)
    try:
      await self._ChatAllHistoryHandler(chat_manager, next_chat_retrieve_begin_message_id, force_update_db=force_update_db)
    except (pyrogram.errors.ChannelPrivate, pyrogram.errors.ChannelInvalid) as e:
      self.logger.error("< GeneralHistoryRetrieve channel is invalid: {}".format(chat_id))
      return False
    self.logger.info("< done GeneralHistoryRetrieve for {}, mode = {}, last message is {}".format(chat_id, history_retrieve_mode, chat_manager.GetLastMessageID()))
    return True

  async def AddManualMessages(self, messages: typing.List[pyrogram.types.Message]):
    for message in messages:
      await self._ManualMessageDispatch(message)

  async def CallbackMessageHandler(self, client, message: pyrogram.types.Message):
    # the handler for all callback message
    chat_id = message.chat.id
    get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is not None:
      await self._GeneralInsertMessage(get_result, message, kChatMessageSourceFromReceive)

  async def RemoveDuplicateMessagesHandler(self, chat_id):
    # the chat id must exist in _chat_id_message_manager_dict
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is None:
      self.logger.info("cannot find {} in _chat_id_message_manager_dict_access_lock".format(chat_id))
      return
    duplicate_messages = await get_result.GetDuplicateMediaMessageIDs()
    self.logger.info("chat {}, need duplicate messages count = {}".format(chat_id, len(duplicate_messages)))

    batch_size = 85
    batch = math.ceil(len(duplicate_messages) / batch_size)
    for i in range(batch):
      self.logger.info("chat {} message remove, processing batch {} / {}".format(chat_id, i, batch))
      await self._telegram_session.client.delete_messages(chat_id, duplicate_messages[i * batch_size: (i+1) * batch_size])
    ret = await get_result.RemoveMessages(duplicate_messages)

    self.logger.info("chat {}, duplicate messages count = {}, done".format(chat_id, len(duplicate_messages)))
    return ret

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
  async def _ChatAllHistoryHandler(self, chat_manager: SingleChatMessageManager, from_message_id: int, force_update_db=False):
    history_gen = self._telegram_session.client.get_chat_history(
        chat_id=chat_manager.GetChatID(), 
        offset_id=from_message_id,
        reverse=True)
    async for message in history_gen:
      # print("message:", message.id)
      await self._GeneralInsertMessage(chat_manager, message, kChatMessageSourceFromHistory, force_update_db=force_update_db)
    # commit if all history is resolved
    await chat_manager.Commit()

  async def _ManualMessageDispatch(self, manual_message: pyrogram.types.Message):
    chat_id = manual_message.chat.id
    get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is not None:
      await self._GeneralInsertMessage(get_result, manual_message, kChatMessageSourceFromManual, callback=False)

  async def _MessageInserted(self, pack: MessageCallbackPack):
    async with self._callback_queue_access_lock:
      await self._callback_queue.put(pack)

  async def _GeneralInsertMessage(self, chat_manager: SingleChatMessageManager, message: pyrogram.types.Message, 
                                  message_source: "ChatMessageSource", force_update_db=False, callback=True):
    insert_dict = await chat_manager.InsertMessage(message, message_source, force_update=force_update_db)
    pack = self._PackAsMessageCallbackPack(message, insert_dict)
    if callback:
      await self._MessageInserted(pack)

  def _PackAsMessageCallbackPack(self, message, message_dict):
    result = MessageCallbackPack()
    result.message = message
    result.message_dict = message_dict
    return result