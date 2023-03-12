
from SQLiteWrapper import *

kChatPermissionInvalidUser = 0
kChatPermissionGuestUser = 10
kChatPermissionNormalUser = 100
kChatPermissionVIPUser = 150
kChatPermissionAdminUser = 199
kChatPermissionSuperUser = 200

ChatPermissions = [
  kChatPermissionInvalidUser,
  kChatPermissionGuestUser,
  kChatPermissionNormalUser,
  kChatPermissionVIPUser,
  kChatPermissionAdminUser,
  kChatPermissionSuperUser,
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

UserForwardStatuses = [
  kUserForwardStatusUnknown,
  kUserForwardStatusSuccess,
  kUserForwardStatusFailDueToInvalidSource,
  kUserForwardStatusFailDueToInvalidUser,
  kUserForwardStatusFailDueToNetworkIssue,
  kUserForwardStatusFailReasonUnrecognized,
] = range(6)

user_status_initiate_dict = {
  "UserStatus": {
    "field_definition": {
      "user_id": "INTEGER",
      "permission": "INTEGER",
      "status": "INTEGER",
      "join_time": "REAL",
      "last_active_time": "REAL",
      "active_expire_time": "REAL",
      "fake_name": "TEXT"
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


bot_help_info_str = """this bot is a media share bot, once you send a media, your active status will be set for 12 hours, stay active to receive media from others"""


minimum_seconds_interval_by_permission = {
  kChatPermissionGuestUser: 28800,   # 8 hours
  kChatPermissionNormalUser: 43200,  # 12 hours
  kChatPermissionVIPUser: 172800,    # 48 hours
  kChatPermissionAdminUser: 1e9,
}

maximum_seconds_interval_by_permission = {
  kChatPermissionGuestUser: 43200,    # 24 hours
  kChatPermissionNormalUser: 43200,  # 96 hours
  kChatPermissionVIPUser: 345600,     # 96 hours
  kChatPermissionAdminUser: 2e9,
}