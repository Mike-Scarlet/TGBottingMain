
from core.path_store_config import PathStoreConfig
from core.telegram_session import TelegramSession
from stage.message.all_chat_messages_manager import *
from stage.mirror.mirror_coordinator import MirrorCoordinator, MessageCallbackPack
from utils.command_parser import ParsedCommand

class LocalMirrorBot:
  def __init__(self, 
               telegram_session: TelegramSession,
               all_chat_message_manager: AllChatMessageManager,
               mirror_coordinator: MirrorCoordinator) -> None:
    self._telegram_session = telegram_session
    self._all_chat_message_manager = all_chat_message_manager
    self._mirror_coordinator = mirror_coordinator
    self._receive_command_chat_id = None
    self._default_mirror_to_chat_id = None

  def SetReceiveCommandChatID(self, chat_id):
    self._receive_command_chat_id = chat_id

  async def MessagePackHandler(self, message_pack: MessageCallbackPack):
    if message_pack.message is None:
      return  # do nothing
    if message_pack.message.text is None:
      return
    if not message_pack.message.text.startswith("/"):
      return
    
    parsed_command = ParsedCommand()
    parsed_command.ParseCommand(message_pack.message.text)
    
    command_key = parsed_command.GetCommandKey()
    command_map = {
      "/add_local_retrieve": self.AddLocalMessageDB,
      "/add_mirror": self.AddMirrorTask,
    }
    get_result = command_map.get(command_key, None)
    if get_result is None:
      return
    await get_result(parsed_command)

  async def SendTextToCommandGroup(self, message_text):
    await self._telegram_session.client.send_message(self._receive_command_chat_id, message_text)

  async def AddLocalMessageDB(self, parsed_command: ParsedCommand):
    if parsed_command.GetParamCount() <= 1:
      return
    chat_id = parsed_command.GetIntParam(0)
    if chat_id is None:
      return

    mode = parsed_command.GetStringParam(1)
    if mode == "from_last":
      mode = kHistoryRetrieveFromLastMessage
    elif mode == "from_begin":
      mode = kHistoryRetrieveFromBegin
    else:
      mode = kHistoryRetrieveFromLastMessage

    await self.SendTextToCommandGroup("start to add local message db: {} - {}".format(
            chat_id, mode))
    await self._all_chat_message_manager.GeneralHistoryRetrieve(chat_id, mode)
    await self.SendTextToCommandGroup("done adding local message db: {} - {}".format(
            chat_id, mode))

  async def AddMirrorTask(self, parsed_command: ParsedCommand):
    if (self._default_mirror_to_chat_id is None and parsed_command.GetParamCount() <= 2) or parsed_command.GetParamCount() <= 1:
      return

    from_chat = parsed_command.GetIntParam(0)
    to_chat = parsed_command.GetIntParam(1)

    if to_chat is None:
      to_chat = self._default_mirror_to_chat_id

    if from_chat is None or to_chat is None:
      return
    
    await self.SendTextToCommandGroup("start to add mirror task: {} -> {}".format(
            from_chat, to_chat))
    await self._mirror_coordinator.AddMirrorTask(from_chat, to_chat)
    await self.SendTextToCommandGroup("done adding mirror task: {} -> {}".format(
            from_chat, to_chat))

  async def ListDialog(self, parsed_command: ParsedCommand):
    max_count = parsed_command.GetIntParam(1)
    if max_count is None:
      max_count = 30

    await self.SendTextToCommandGroup("start retrive {} dialogs".format(
            max_count))
    all_dialogs = await self._telegram_session.GetAllDialogsAsync(max_count)
    result_lines = []
    for name, dialog in all_dialogs:
      result_lines.append("{}: {}".format(name, dialog.chat.id))
      if len(result_lines) > max_count:
        break
    await self.SendTextToCommandGroup("\n".join(result_lines))

  # TODO: reboot
  # TODO: mirror restart