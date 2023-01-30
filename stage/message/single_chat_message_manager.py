
from sql.message.single_chat_message_sql import single_chat_message_table_structure
from SQLiteWrapper import *
import pyrogram
import asyncio
import time

ChatMessageSource = [
  kChatMessageSourceFromHistory,
  kChatMessageSourceFromReceive,
  kChatMessageSourceFromManual,
] = range(3)

class SingleChatMessageManager:
  """ just do message management """
  def __init__(self, chat_id=None, db_path=None) -> None:
    self._chat_id = chat_id
    self._db_path = db_path
    self._db_access_lock = asyncio.Lock()

    self._conn = None
    self._op = None

    # cache
    self._message_id_set = set()
    self._file_unique_id_set = set()

    # commit info
    self._last_commit_timestamp = 0
    self._commit_interval_seconds = 10.0

  def GetChatID(self):
    return self._chat_id

  """ initiate interfaces """
  def SetDBPath(self, db_path):
    self._db_path = db_path

  async def InitiateDB(self):
    if self._db_path is None:
      raise ValueError("db path is none for SingleChatMessageManager")
    async with self._db_access_lock:
      self._conn = SQLite3Connector(
        self._db_path,
        single_chat_message_table_structure
      )
      self._conn.Connect(do_check=False)
      self._conn.TableValidation()
      self._op = SQLite3Operator(self._conn)

  async def InitiateMessageIDSet(self):
    async with self._db_access_lock:
      select_result = self._op.SelectFieldFromTable(["id"], "Messages")
      self._message_id_set = set(map(lambda x: x["id"], select_result))

  async def InitiateFileUniqueIDSet(self):
    async with self._db_access_lock:
      select_result = self._op.SelectFieldFromTable(["file_unique_id"], "Messages")
      self._file_unique_id_set = set(map(lambda x: x["file_unique_id"], select_result))

  """ insert interfaces """
  async def InsertMessage(self, 
                          message: pyrogram.types.Message, 
                          message_source: "ChatMessageSource",
                          force_update=False):
    # translate message to insert dict
    # pyrogram.enums.message_media_type.MessageMediaType
    # pyrogram.types.messages_and_media
    insert_dict = self._PyrogramMessageToInsertDict(message, message_source)
    async with self._db_access_lock:
      if force_update:
        self._op.InsertDictToTable(insert_dict, "Messages", "OR REPLACE")
      else:
        self._op.InsertDictToTable(insert_dict, "Messages", "OR IGNORE")
      self._message_id_set.add(insert_dict["id"])
      fui = insert_dict.get("file_unique_id", None)
      if fui is not None:
        self._file_unique_id_set.add(fui)
      if abs(self._last_commit_timestamp - time.time()) > self._commit_interval_seconds:
        await self.Commit(lock=False)
    return insert_dict

  async def Commit(self, lock=True):
    if lock:
      async with self._db_access_lock:
        self._op.Commit()
        self._last_commit_timestamp = time.time()
    else:
      self._op.Commit()
      self._last_commit_timestamp = time.time()
      

  """ query interfaces """
  def IsFileUniqueIDExists(self, file_unique_id):
    return file_unique_id in self._file_unique_id_set

  def GetLastMessageID(self):
    if len(self._message_id_set) == 0:
      return -1
    return max(self._message_id_set)

  """ private functions """
  def _PyrogramMessageToInsertDict(self, message: pyrogram.types.Message, message_source: "ChatMessageSource"):
    insert_dict = {
      "id": message.id,
      "message_source": message_source,
    }
    if message.chat is not None:
      insert_dict["chat_id"] = message.chat.id
    if message.date is not None:
      insert_dict["date"] = message.date.timestamp()
    if message.edit_date is not None:
      insert_dict["edit_date"] = message.edit_date.timestamp()
    if message.media is not None:
      # a media message, do media message handler
      insert_dict["media"] = message.media.name
      if message.media_group_id is not None:
        insert_dict["media_group_id"] = message.media_group_id
      media_content = getattr(message, message.media.value)
      if hasattr(media_content, "file_id"):
        insert_dict["file_id"] = media_content.file_id
      if hasattr(media_content, "file_unique_id"):
        insert_dict["file_unique_id"] = media_content.file_unique_id
    if message.service is not None:
      insert_dict["service"] = message.service.name
    if message.author_signature is not None:
      insert_dict["author_signature"] = message.author_signature
    if message.text is not None:
      insert_dict["text"] = message.text
    if message.caption is not None:
      insert_dict["caption"] = message.caption
    return insert_dict