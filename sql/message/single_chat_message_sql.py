
from SQLiteWrapper import *

single_chat_message_initiate_dict = {
  "LocalRetrieve": {
    "field_definition": {
      # > MAIN FIELDS
      "chat_id": "INTEGER UNIQUE NOT NULL",
    },
    "primary_keys": "chat_id"
  },
  "Mirror": {
    "field_definition": {
      # > MAIN FIELDS
      "mirror_from_id": "INTEGER UNIQUE NOT NULL",
      "mirror_to_id": "INTEGER UNIQUE NOT NULL",
    },
    "primary_keys": ["mirror_from_id", "mirror_to_id"]
  }
}

single_chat_message_table_structure = SQLDatabase.CreateFromDict(single_chat_message_initiate_dict)