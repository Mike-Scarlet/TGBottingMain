
from SQLiteWrapper import *

mirror_coordinator_initiate_dict = {
  "MirrorTasks": {
    "field_definition": {
      "from_chat_id": "TEXT NOT NULL",
      "to_chat_id": "TEXT NOT NULL",
      "is_active": "INTEGER",
    },
    "primary_keys": ["from_chat_id", "to_chat_id"]
  },
  "FailInfo": {
    "field_definition": {
      "from_chat_id": "TEXT NOT NULL",
      "to_chat_id": "TEXT NOT NULL",
      "need_to_send_messages": "TEXT NOT NULL",
      "disable_notification": "INTEGER NOT NULL",
      "protect_content": "INTEGER NOT NULL",
      "current_status:": "INTEGER"
    }
  }
}

mirror_coordinator_table_structure = SQLDatabase.CreateFromDict(mirror_coordinator_initiate_dict)