
from SQLiteWrapper import *

kChatPermissionInvalidUser = 0
kChatPermissionGuestUser = 10
kChatPermissionNormalUser = 100
kChatPermissionVIPUser = 150
kChatPermissionAdminUser = 199
kChatPermissionSuperUser = 200

ChatPermissions = [
  kChatPermissionInvalidUser,
  kChatPermissionAdminUser,
  kChatPermissionVIPUser,
  kChatPermissionNormalUser,
  kChatPermissionGuestUser,
]

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
      "active_expire_time": "REAL",
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
