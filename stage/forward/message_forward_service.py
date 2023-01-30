
from core.telegram_session import *

class MessageForwardPack:
  def __init__(self) -> None:
    self.from_chat_id = None
    self.from_chat_id_messages = None
    self.to_chat_id = None
    self.disable_notification = True
    self.protect_content = False

class MessageForwardService:
  def __init__(self, telegram_session: TelegramSession) -> None:
    self._telegram_session = telegram_session
    self._forward_queue = asyncio.Queue(1)
    self._wait_seconds_per_forward = 0.1

  async def AddForwardPack(self, forward_pack: MessageForwardPack):
    await self._forward_queue.put(forward_pack)

  async def RunServiceLoopForever(self):
    while True:
      pack: MessageForwardPack = await self._forward_queue.get()
      await self._telegram_session.client.forward_messages(pack.to_chat_id, pack.from_chat_id, pack.from_chat_id_messages, 
                                                           disable_notification=pack.disable_notification, 
                                                           protect_content=pack.protect_content)
      await asyncio.sleep(max(0.5, len(pack.from_chat_id_messages) * self._wait_seconds_per_forward))