
from core.telegram_session import TelegramSession
from stage.message.all_chat_messages_manager import AllChatMessageManager, kHistoryRetrieveFromLastMessage, MessageCallbackPack
from sql.mirror.mirror_coordinator_sql import *
from stage.global_functions import *
import logging
import os
import typing
import asyncio
import collections

class SingleMirrorDistributeHandler:
  def __init__(self, 
               mirror_from_chat: str, 
               mirror_to_chat: str, 
               all_chat_message_manager: AllChatMessageManager) -> None:
    self._mirror_from_chat = mirror_from_chat
    self._mirror_to_chat = mirror_to_chat
    self._all_chat_message_manager = all_chat_message_manager
    self._replicate_media_batch = 90
    self._logger = logging.getLogger("SingleMirrorDistributeHandler")

    self._replicate_insert_message_queue = asyncio.Queue(10)
    self._task = None

  def GetMirrorToChat(self):
    return self._mirror_to_chat

  async def AddDistributeSourceMessage(self, message_pack: MessageCallbackPack):
    await self._replicate_insert_message_queue.put(message_pack)

  async def StopForwardHandling(self):
    await self.AddDistributeSourceMessage(None)
    self._logger.info("prepare to stop: {} -> {}".format(self._mirror_from_chat, self._mirror_to_chat))
    await self._task
    self._logger.info("stopped: {} -> {}".format(self._mirror_from_chat, self._mirror_to_chat))

  async def StartTask(self, telegram_session: TelegramSession):
    self._task = telegram_session.loop.create_task(self._MainTaskLoop())

  async def _MainTaskLoop(self):
    need_to_insert_message_packs: typing.List[MessageCallbackPack] = []
    while True:
      # TODO: INSTANT
      first_get_result = await self._replicate_insert_message_queue.get()
      if first_get_result is None:
        return  # stop the loop

      fail_counter = 0
      need_to_insert_message_packs.append(first_get_result)
      exit_loop = False
      while True:
        try:
          another_get_result = self._replicate_insert_message_queue.get_nowait()
          if another_get_result is None:
            exit_loop = True
            break   # direct stop
          fail_counter = 0
        except asyncio.QueueEmpty:
          # queue empty
          if fail_counter <= 0:
            fail_counter += 1
            await asyncio.sleep(1)  # sleep for 1 second, then retry
            continue
          else:
            # stop
            break
        do_forward_first = False
        if len(need_to_insert_message_packs) >= self._replicate_media_batch:
          # check if new pack has same media batch id with exist
          if need_to_insert_message_packs[-1].message_dict["media_group_id"] is None or \
                need_to_insert_message_packs[-1].message_dict["media_group_id"] != \
                another_get_result.message_dict["media_group_id"]:
            do_forward_first = True

        if do_forward_first:
          # construct forward pack
          await self.ForwardMessageByPacks(need_to_insert_message_packs)
          need_to_insert_message_packs = []
        # simple add
        need_to_insert_message_packs.append(another_get_result)
      if len(need_to_insert_message_packs) > 0:
        # insert final
        await self.ForwardMessageByPacks(need_to_insert_message_packs)
        need_to_insert_message_packs = []
      if exit_loop:
        return

  async def ForwardMessageByPacks(self, packs: typing.List[MessageForwardPack]):
    forward_pack = MessageForwardPack()
    forward_pack.from_chat_id = self._mirror_from_chat
    forward_pack.to_chat_id = self._mirror_to_chat
    forward_pack.from_chat_id_messages = list(map(lambda x: x["id"], packs))
    await GlobalForwardMessage(forward_pack)   # TODO: fail process


class MirrorCoordinator:
  _mirror_from_chat_to_handlers_dict: typing.Dict[typing.Union[str, int], typing.List[SingleMirrorDistributeHandler]]
  def __init__(self, 
               telegram_session: TelegramSession,
               mirror_coordinator_work_folder: str,
               all_chat_message_manager: AllChatMessageManager) -> None:
    self._telegram_session = telegram_session
    self._mirror_coordinator_work_folder = mirror_coordinator_work_folder
    self._all_chat_message_manager = all_chat_message_manager
    if not os.path.exists(self._mirror_coordinator_work_folder):
      os.makedirs(self._mirror_coordinator_work_folder)

    self._db_access_lock = asyncio.Lock()

    self._conn = None
    self._op = None

    self._handler_access_lock = asyncio.Lock()
    self._mirror_from_chat_to_handlers_dict = collections.defaultdict(list)

    self._logger = logging.getLogger("MirrorCoordinator")

  async def Initiate(self):
    if self._mirror_coordinator_work_folder is None:
      raise ValueError("self._mirror_coordinator_work_folder is None")
    if self._all_chat_message_manager is None:
      raise ValueError("self._all_chat_message_manager is None")

    db_path = os.path.join(self._mirror_coordinator_work_folder, "coordinator.db")
    async with self._db_access_lock:
      self._conn = SQLite3Connector(
        db_path,
        mirror_coordinator_table_structure
      )
      self._conn.Connect(do_check=False)
      self._conn.TableValidation()
      self._op = SQLite3Operator(self._conn)

    await self._HandleExistTasks()

  async def HandleCallbackPack(self, pack: MessageCallbackPack):
    print("in: ", pack.message_dict)
    if pack.message_dict.get("media", None) in (None, "STICKER", "ANIMATION", "VOICE"):
      return  # do not forward
    if pack.message_dict.get("file_unique_id", None) is None:
      return  # not a file
    from_chat_id = pack.message_dict.get("chat_id", None)
    handlers_list = self._mirror_from_chat_to_handlers_dict.get(from_chat_id, None)
    if handlers_list is None:
      return
    for handler in handlers_list:
      to_chat = handler.GetMirrorToChat()
      chat_manager = await self._all_chat_message_manager.GetSingleChatManager(to_chat)
      if chat_manager is None:
        self._logger.error("cannot find chat manager")
        continue
      if chat_manager.IsFileUniqueIDExists(pack.message_dict["file_unique_id"]):
        continue
      await handler.AddDistributeSourceMessage(pack)

  async def AddMirrorTask(self, from_chat_id, to_chat_id):
    db_insert_dict = {
      "from_chat_id": from_chat_id,
      "to_chat_id": to_chat_id,
      "is_active": 1
    }
    async with self._db_access_lock:
      self._op.InsertDictToTable(db_insert_dict, "MirrorTasks", "OR REPLACE")

    await self._AddMirrorDistribute(from_chat_id, to_chat_id)
    await self._all_chat_message_manager.GeneralHistoryRetrieve(from_chat_id, kHistoryRetrieveFromLastMessage)

  async def _HandleExistTasks(self):
    select_results = self._op.SelectFieldFromTable("*", "MirrorTasks")
    for task_dict in select_results:
      if task_dict["is_active"] == 0:
        continue
      await self._AddMirrorDistribute(task_dict["from_chat_id"], task_dict["to_chat_id"])
    for task_dict in select_results:
      if task_dict["is_active"] == 0:
        continue
      await self._all_chat_message_manager.GeneralHistoryRetrieve(task_dict["to_chat_id"], kHistoryRetrieveFromLastMessage)
    for task_dict in select_results:
      if task_dict["is_active"] == 0:
        continue
      await self._all_chat_message_manager.GeneralHistoryRetrieve(task_dict["from_chat_id"], kHistoryRetrieveFromLastMessage)

  async def _AddMirrorDistribute(self, from_chat_id, to_chat_id):
    handler = SingleMirrorDistributeHandler(from_chat_id, to_chat_id, self._all_chat_message_manager)
    async with self._handler_access_lock:
      self._mirror_from_chat_to_handlers_dict[from_chat_id].append(handler)
      await handler.StartTask(self._telegram_session)