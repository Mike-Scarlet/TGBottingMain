
from SQLiteWrapper import *

local_mirror_bot_status_initiate_dict = {
  "Messages": {
    "field_definition": {
      # > MAIN FIELDS
      
      "id": "INTEGER UNIQUE NOT NULL",
      "chat_id": "TEXT",
      "from_user": "INTEGER",
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
      # > USER FIELDS
      "__is_removed": "INTEGER DEFAULT 0",
    },
    "primary_keys": "id"
  }
}

local_mirror_bot_status_table_structure = SQLDatabase.CreateFromDict(local_mirror_bot_status_initiate_dict)