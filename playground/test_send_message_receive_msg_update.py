
from core.telegram_session_config import *
from core.telegram_session import *
import argparse
import collections

async def MessageListeningProcess(client, message: pyrogram.types.Message):
  print("message received")
  print(message)
  if message.chat.id != 5417885784:
    return
  

async def main():
  # parser = argparse.ArgumentParser()
  # args = parser.parse_args()

  telegram_sess_cfg = TelegramSessionConfig()
  telegram_sess_cfg.LoadFromJsonFile("config/another_session_config.json")

  telegram_sess = TelegramSession(telegram_sess_cfg)
  await telegram_sess.StartSessionAsync()

  # # test multiple media -> 'media_group_id'
  # async def TEST_HANDLER():
  #   history_gen = telegram_sess.client.get_chat_history(
  #       chat_id=-1001802018080, 
  #       offset_id=0,
  #       reverse=True)
  #   async for message in history_gen:
  #     print(message)
  #     pass

  # history_gen = telegram_sess.client.get_chat_history(
  #   chat_id=-1001819499404, 
  #   offset_id=0,
  #   reverse=True)
  # type_count_map = collections.defaultdict(int)
  # async for message in history_gen:
  #   type_count_map[message.media] += 1
  # print(type_count_map)

  # # # list dialogs
  # await telegram_sess.ListAllDialogsAsync()

  telegram_sess.client.add_handler(
    pyrogram.handlers.MessageHandler(MessageListeningProcess),
    group=0
  )

  await asyncio.sleep(1)

  # pyrogram.types.MessageEntity  # to add button
  for i in range(2):
    print("start send")
    sent_msg = await telegram_sess.client.send_message(5417885784, text="current message_seq: {}".format(i))
    telegram_sess.client.forward_messages()
    await asyncio.sleep(1)

  # wait for all
  await pyrogram.idle()

if __name__ == "__main__":
  asyncio.run(main())