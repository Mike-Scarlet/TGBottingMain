
"""
user info db
message process queue
"""

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

class ChannelChatUserStatus:
  def __init__(self) -> None:
    self.permission = kChatPermissionInvalidUser
    self.status = kChatStatusInactive
    self.last_active_time = 0

class FromMessages:
  pass

class BotChannelChatMain:
  def __init__(self) -> None:
    pass

  async def PrepareHandlers(self):
    # TODO:
    pass

  