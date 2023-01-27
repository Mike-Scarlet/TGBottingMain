
import typing
from stage.message.single_chat_message_manager import *

class AllChatMessageManager:
  _chat_id_message_manager_dict: typing.Dict[int, SingleChatMessageManager]

  def __init__(self) -> None:
    self._chat_id_message_manager_dict = {}
    self._chat_id_message_manager_dict_access_lock = asyncio.Lock()

  def GeneralHistoryRetrieve(self, chat_id):
    pass

  def ManualMessageDispatch(self, manual_message):
    pass

  def ChatAllHistoryHandler(self):
    pass

  def CallbackMessageHandler(self):
    pass