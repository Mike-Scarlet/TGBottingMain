
from sql.message.single_chat_message_sql import single_chat_message_table_structrue
from SQLiteWrapper import *
import pyrogram
import asyncio

ChatMessageSource = [
  kChatMessageSourceFromHistory,
  kChatMessageSourceFromReceive,
  kChatMessageSourceFromManual,
] = range(3)

class SingleChatMessageManager:
  """ just do message management """
  def __init__(self, db_path=None) -> None:
    self._db_path = db_path
    self._db_access_lock = asyncio.Lock()

    self._conn = None
    self._op = None

  """ initiate interfaces """
  def SetDBPath(self, db_path):
    self._db_path = db_path

  async def InitiateDB(self):
    if self._db_path is None:
      raise ValueError("db path is none for SingleChatMessageManager")
    with self._db_access_lock:
      self._conn = SQLite3Connector(
        self._db_path,
        single_chat_message_table_structrue
      )
      self._conn.Connect(do_check=False)
      self._conn.TableValidation()
      self._op = SQLite3Operator(self._conn)

  """ insert interfaces """
  async def InsertMessage(self, message: pyrogram.types.Message, message_source: "ChatMessageSource"):
    # translate message to insert dict
    # pyrogram.enums.message_media_type.MessageMediaType
    # pyrogram.types.messages_and_media
    insert_dict = self.PyrogramMessageToInsertDict(message, message_source)
    self._op.InsertDictToTable(insert_dict, "Messages", "OR IGNORE")

  async def Commit(self):
    self._op.Commit()

  """ query interfaces """


  """ private functions """
  def PyrogramMessageToInsertDict(self, message: pyrogram.types.Message, message_source: "ChatMessageSource"):
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
        insert_dict["file_id"] = media_content.file_unique_id
      # TODO: more fields
    if message.service is not None:
      insert_dict["service"] = message.service.name
    if message.author_signature is not None:
      insert_dict["author_signature"] = message.author_signature
    if message.text is not None:
      insert_dict["text"] = message.text
    if message.caption is not None:
      insert_dict["caption"] = message.caption
    return insert_dict