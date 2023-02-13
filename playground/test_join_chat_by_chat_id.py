
from python_general_lib.environment_setup.logging_setup import *
from core.path_store_config import *
from core.telegram_session_config import *
from core.telegram_session import *
from stage.message import *

import argparse
import collections

async def main():
  # parser = argparse.ArgumentParser()
  # args = parser.parse_args()

  store_cfg = PathStoreConfig()
  store_cfg.LoadFromJsonFile("config/all_path_definition.json")

  telegram_sess_cfg = TelegramSessionConfig()
  telegram_sess_cfg.LoadFromJsonFile("config/another_session_config.json")

  telegram_sess = TelegramSession(telegram_sess_cfg)
  await telegram_sess.StartSessionAsync()

  # await telegram_sess.ListAllDialogsAsync()

  join_result = await telegram_sess.client.join_chat(-1001811841908)
  pass

  # all_chat_message_manager = AllChatMessageManager(telegram_sess, store_cfg.all_chat_db_store_folder)
  # telegram_sess.client.add_handler(
  #   pyrogram.handlers.MessageHandler(all_chat_message_manager.CallbackMessageHandler),
  #   group=0
  # )

  # # def DummyFunction(message_pack: MessageCallbackPack):
  # #   print(message_pack.message_dict)

  # callback_pack_handler = MessageCallbackPackHandler()
  # callback_pack_handler.SetMessageCallbackPackQueue(all_chat_message_manager.GetCallbackQueue())
  # # callback_pack_handler.AddFunction(DummyFunction)
  # callback_task = telegram_sess.loop.create_task(callback_pack_handler.RunServiceLoopForever())

  # # await all_chat_message_manager.GeneralHistoryRetrieve(-896909962)
  # # # await all_chat_message_manager.GeneralHistoryRetrieve(-896909962, kHistoryRetrieveFromBegin, True)
  # # await all_chat_message_manager.RemoveDuplicateMessagesHandler(-896909962)

  # chat_id = -820020834
  # await all_chat_message_manager.GeneralHistoryRetrieve(chat_id)
  # await all_chat_message_manager.RemoveDuplicateMessagesHandler(chat_id)

  # wait for all
  await pyrogram.idle()

if __name__ == "__main__":
  asyncio.run(main())