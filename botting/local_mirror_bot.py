
from core.path_store_config import PathStoreConfig
from core.telegram_session import TelegramSession
from stage.message.all_chat_messages_manager import AllChatMessageManager
from stage.mirror.mirror_coordinator import MirrorCoordinator, MessageCallbackPack

class LocalMirrorBot:
  def __init__(self, 
               telegram_session: TelegramSession,
               all_chat_message_manager: AllChatMessageManager,
               mirror_coordinator: MirrorCoordinator) -> None:
    self._telegram_session = telegram_session
    self._all_chat_message_manager = all_chat_message_manager
    self._mirror_coordinator = mirror_coordinator
    self._receive_command_chat_id = None

  def SetReceiveCommandChatID(self, chat_id):
    self._receive_command_chat_id = chat_id

  async def MessagePackHandler(self, message_pack: MessageCallbackPack):
    if message_pack.message is None:
      return  # do nothing
    
    pass