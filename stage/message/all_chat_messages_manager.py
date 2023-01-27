
import typing
from stage.message.single_chat_message_manager import *

class AllChatMessageManager:
  _chat_id_message_manager_dict: typing.Dict[int, SingleChatMessageManager]

  def __init__(self) -> None:
    self._chat_id_message_manager_dict = {}
    self._chat_id_message_manager_dict_access_lock = asyncio.Lock()

  async def GeneralHistoryRetrieve(self, chat_id):
    pass

  async def ChatAllHistoryHandler(self, chat_id, reload=False):
    pass

  async def CallbackMessageHandler(self):
    pass

  async def ManualMessageDispatch(self, manual_message):
    pass