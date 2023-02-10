
from core.telegram_session import *
from utils.periodic_restriction import PeriodicRestriction
import logging

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
    self._wait_seconds_per_forward = 0.1

    self._send_lock = asyncio.Lock()
    self._logger = logging.getLogger("MessageForwardService")

    self._message_forwarded_callback_async = None  # param is list of messages
    self._message_forward_failure_callback_async = None  # param is message forward pack

    self._forward_restriction_helper = PeriodicRestriction()
    self._forward_restriction_helper.SetPeriod(3600)  # 1 hour
    self._forward_restriction_helper.SetRestrictCount(1500)  # 1500 messages

  def SetForwardedCallbackAsyncFunction(self, async_fn):
    self._message_forwarded_callback_async = async_fn

  def SetForwardFailureCallbackAsyncFunction(self, async_fn):
    self._message_forward_failure_callback_async = async_fn

  async def AddForwardPack(self, pack: MessageForwardPack) -> bool:
    send_result = False
    retry_count = 0
    async with self._send_lock:
      while True:
        try:
          forward_result = await self._telegram_session.client.forward_messages(
              pack.to_chat_id, pack.from_chat_id, pack.from_chat_id_messages, 
              disable_notification=pack.disable_notification, 
              protect_content=pack.protect_content)
          if self._message_forwarded_callback_async is not None:
            if isinstance(forward_result, pyrogram.types.Message):
              forward_result = [forward_result]
            await self._message_forwarded_callback_async(forward_result)
          self._logger.info("[{} -> {}] forwarded {} messages".format(pack.from_chat_id, pack.to_chat_id, len(pack.from_chat_id_messages)))
          await asyncio.sleep(max(0.5, len(pack.from_chat_id_messages) * self._wait_seconds_per_forward))
          send_result = True
          # post add
          await self._forward_restriction_helper.AddCountByNowAsyncPreCheck(len(forward_result))
          break
        except pyrogram.errors.flood_420.FloodWait as e:
          print(e)
          if retry_count >= 2:
            self._logger.warning("retry too much times")
            break
          retry_count += 1
          await asyncio.sleep(e.value + 2.0)
          continue
        except Exception as e:
          if self._message_forward_failure_callback_async is not None:
            await self._message_forward_failure_callback_async(pack)
          print(e)
          print("will not forward anymore")
          break
    return send_result