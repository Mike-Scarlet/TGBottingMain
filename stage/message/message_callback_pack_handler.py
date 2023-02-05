
import asyncio

class MessageCallbackPackHandler:
  _message_callback_pack_queue: asyncio.Queue
  def __init__(self) -> None:
    self._message_callback_pack_queue = None
    self._pack_handler_functions = []
    self._pack_handler_async_functions = []

  def AddFunction(self, f):
    if asyncio.iscoroutinefunction(f):
      self._pack_handler_async_functions.append(f)
    else:
      self._pack_handler_functions.append(f)

  def RemoveFunction(self, f):
    if asyncio.iscoroutinefunction(f):
      try:
        self._pack_handler_async_functions.remove(f)
      except:
        pass
    else:
      try:
        self._pack_handler_functions.remove(f)
      except:
        pass

  def SetMessageCallbackPackQueue(self, q):
    self._message_callback_pack_queue = q

  async def RunServiceLoopForever(self):
    if self._message_callback_pack_queue is None:
      raise ValueError("self._message_callback_pack_queue is None")
    while True:
      pack = await self._message_callback_pack_queue.get()
      # print("processing pack:", pack.message_dict)
      for function in self._pack_handler_functions:
        function(pack)
      for function in self._pack_handler_async_functions:
        # print("async process")
        await function(pack)
        # print("async done")