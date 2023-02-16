
from SQLiteWrapper import *

from_messages_initiate_dict = {
  "FromMessages": {
    "field_definition": {
      "from_user_id": "INTEGER",
      "from_message_id": "INTEGER",
      "media_unique_id": "TEXT"
    },
    "primary_keys": ["from_chat_id", "from_message_id"]
  }
}

from_messages_table_structure = SQLDatabase.CreateFromDict(from_messages_initiate_dict)

ChatPermissions = [
  kChatPermissionInvalidUser,
  kChatPermissionNormalUser,
  kChatPermissionVIPUser,
  kChatPermissionAdminUser,
] = range(4)

ChatStatuses = [
  kChatStatusInactive,
  kChatStatusActive,
  kChatStatusMute,
] = range(3)
