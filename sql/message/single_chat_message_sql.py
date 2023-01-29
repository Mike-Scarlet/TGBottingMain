
from SQLiteWrapper import *

single_chat_message_initiate_dict = {
  "Messages": {
    "field_definition": {
      # > MAIN FIELDS
      "id": "INTEGER UNIQUE NOT NULL",
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
      # > SUB FIELDS
      "file_id": "TEXT",
      "file_unique_id": "TEXT",  # use this to map to file key
      "message_source": "INTEGER",  # usage
    },
    "primary_keys": "id"
  }
}

single_chat_message_table_structure = SQLDatabase.CreateFromDict(single_chat_message_initiate_dict)