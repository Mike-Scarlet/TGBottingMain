
__all__ = [
  "MessageForwardPack",
  "GlobalForwardMessage",
  "SetGlobalMessageForwardService",
]

from stage.forward.message_forward_service import MessageForwardPack, MessageForwardService

_global_message_forward_service: MessageForwardService = None

def SetGlobalMessageForwardService(service):
  global _global_message_forward_service
  _global_message_forward_service = service

async def GlobalForwardMessage(forward_pack: MessageForwardPack) -> bool:
  return await _global_message_forward_service.AddForwardPack(forward_pack)