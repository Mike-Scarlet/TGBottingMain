
from http_bots.bot_channel_chat.bot_channel_chat_constants import *

class ForwardTask:
  def __init__(self) -> None:
    self.task_index = None
    self.from_user_id = None
    self.from_message_id = None
    self.file_unique_id = None
    self.total_need_to_forward_count = 0

class ForwardCommand:
  task: ForwardTask
  def __init__(self) -> None:
    self.task = None
    self.to_user_id = None
    self.user_forward_status = kUserForwardStatusUnknown

class ChannelChatUserStatus:
  def __init__(self) -> None:
    self.user_id = None
    self.permission = kChatPermissionInvalidUser
    self.status = kChatStatusInactive
    self.join_time = 0
    self.last_active_time = 0
    self.active_expire_time = 0