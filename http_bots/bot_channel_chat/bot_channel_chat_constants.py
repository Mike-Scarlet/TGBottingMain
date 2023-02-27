
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


bot_help_info_str = """机器人说明
本机器人为媒体转发机器人，若您为活跃状态，则可以接收到其他人向机器人中发送的媒体。
保持活跃状态有两种方式，发送/join和发送媒体，其中发送/join会将您的活跃状态刷新至{}小时，发送媒体还会根据媒体类型将活跃状态延长（视频2.5小时，图片1小时），该时间可以累计，激活时间延长的最长时限为{}小时。您可以发送/current_status来确认您的活跃时间剩余时长。
禁止事项
1. 发送彻底无关的视频或图片（纯色图片，手机截图等） → 活跃状态会被取消
2. 刷屏彻底无关的视频或图片 → 会被ban
3. 发送广告 → 会被ban
<尽量少发成人内容哦>
<大家一起快乐分享吧>"""