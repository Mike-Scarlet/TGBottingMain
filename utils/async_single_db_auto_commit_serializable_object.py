
from utils.single_db_serializable_object import *
from utils.async_timed_trigger import AsyncTimedTrigger
import asyncio

class AsyncSingleDBAutoCommitSerializableObject(SingleDBSerializableObject):
  def __init__(self, db_path:str=None, table_structure:SQLDatabase=None) -> None:
    super().__init__(db_path, table_structure)

    # commit trigger
    self._timed_trigger = AsyncTimedTrigger()
    self._timed_trigger.SetMustCallCallbackTimeInterval(20.0)

    self._lock = asyncio.Lock()

  def SetTriggerMustCallBackInterval(self, interval):
    self._timed_trigger.SetMustCallCallbackTimeInterval(interval)

  async def AutoCommitAfter(self, seconds):
    await self._timed_trigger.ActivateTimedTrigger(seconds)

  async def Initiate(self, loop: asyncio.AbstractEventLoop):
    super().InitiateDB()
    self._timed_trigger.SetCallbackAsyncFunction(self.CommitAsync)
    await self._timed_trigger.StartTriggerHandlerTask(loop)

  async def CommitAsync(self, lock=True):
    if self._op is None:
      return
    if lock:
      async with self._lock:
        self._op.Commit()
    else:
      self._op.Commit()