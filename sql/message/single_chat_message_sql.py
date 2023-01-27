
from SQLiteWrapper import *
import pyrogram

pyrogram.types.Message

single_chat_message_initiate_dict = {
  "Messages": {
    "id": "INTEGER NOT NULL",
    "chat_id": "TEXT",
    "date": "INTEGER",  # timestamp from utc
    "edit_date": "INTEGER",  # timestamp from utc
    "media": "TEXT",   # pyrogram.enums.MessageMediaType
    "service": "TEXT",   # pyrogram.enums.MessageServiceType
    "media_group_id": "TEXT",
    "author_signature": "TEXT",
    "text": "TEXT",
    "caption": "TEXT",
    # "entities",
    # "caption_entities",

  }
}