
import typing
from stage.message.single_chat_message_manager import *
import os

HistoryRetriveModes = [
  kHistoryRetrieveFromBegin,
  kHistoryRetrieveFromLastMessage,
] = range(2)

class AllChatMessageManager:
  _chat_id_message_manager_dict: typing.Dict[int, SingleChatMessageManager]

  def __init__(self, all_chat_db_store_path) -> None:
    self._all_chat_db_store_path = all_chat_db_store_path
    if not os.path.exists(self._all_chat_db_store_path):
      os.makedirs(self._all_chat_db_store_path)
    self._chat_id_message_manager_dict = {}
    self._chat_id_message_manager_dict_access_lock = asyncio.Lock()

  async def GetOrCreateChatManager(self, chat_id) -> SingleChatMessageManager:
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
    if get_result is None:
      get_result = SingleChatMessageManager(
        chat_id,
        os.path.join(self._all_chat_db_store_path, "{}.db".format(chat_id)))
      get_result.InitiateDB()
      get_result.InitiateMessageIDSet()
      get_result.InitiateFileUniqueIDSet()
    return get_result

  async def StopTrackChatManager(self, chat_id):
    async with self._chat_id_message_manager_dict_access_lock:
      get_result = self._chat_id_message_manager_dict.get(chat_id, None)
      if get_result is not None:
        get_result.Commit()
        del self._chat_id_message_manager_dict[chat_id]

  async def AddChatManager(self, single_chat_manager: SingleChatMessageManager):
    async with self._chat_id_message_manager_dict_access_lock:
      if single_chat_manager.GetChatID() not in self._chat_id_message_manager_dict:
        self._chat_id_message_manager_dict[single_chat_manager.GetChatID()] = single_chat_manager
      else:
        pass

  async def GeneralHistoryRetrieve(self, chat_id, history_retrieve_mode=kHistoryRetrieveFromLastMessage):
    chat_manager = await self.GetOrCreateChatManager(chat_id)
    next_chat_retrieve_begin_message_id = 0
    if history_retrieve_mode == kHistoryRetrieveFromLastMessage:
      # need to get max message id from chat manager
      next_chat_retrieve_begin_message_id = chat_manager.GetLastMessageID() + 1
    await self.AddChatManager(chat_id)
    # TODO:


  async def ChatAllHistoryHandler(self, chat_manager, from_message_id):
    pass

  async def ManualMessageDispatch(self, manual_message):
    pass

  async def CallbackMessageHandler(self):
    # the handler for all callback message
    pass