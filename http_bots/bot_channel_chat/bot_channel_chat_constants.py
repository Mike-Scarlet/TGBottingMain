
from SQLiteWrapper import *

ChatPermissions = [
  kChatPermissionInvalidUser,
  kChatPermissionAdminUser,
  kChatPermissionVIPUser,
  kChatPermissionNormalUser,
  kChatPermissionGuestUser,
] = range(5)

ChatStatuses = [
  kChatStatusInactive,
  kChatStatusActive,
  kChatStatusMute,
] = range(3)

ForwardStatuses = [
  kForwardStatusInQueue,
  kForwardStatusDone,
  kForwardStatusInvalid,
] = range(3)

user_status_initiate_dict = {
  "UserStatus": {
    "field_definition": {
      "user_id": "INTEGER",
      "permission": "INTEGER",
      "status": "INTEGER",
      "join_time": "REAL",
      "last_active_time": "REAL",
    },
    "primary_keys": ["user_id"]
  }
}

user_status_table_structure = SQLDatabase.CreateFromDict(user_status_initiate_dict)

from_messages_initiate_dict = {
  "FromMessages": {
    "field_definition": {
      "from_user_id": "INTEGER",
      "from_message_id": "INTEGER",
      "task_index": "INTEGER",
      "file_unique_id": "TEXT",
      "forward_status": "INTEGER",
      "add_time": "REAL",
    },
    "primary_keys": ["from_user_id", "from_message_id"]
  }
}

from_messages_table_structure = SQLDatabase.CreateFromDict(from_messages_initiate_dict)
