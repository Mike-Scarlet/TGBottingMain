
import time
import asyncio
import logging

class AsyncTimedTrigger:
  def __init__(self) -> None:
    self._logger = logging.getLogger("AsyncTimedTrigger")
    self._extern_time_access_lock = asyncio.Lock()
    self._trigger_pad_time = 0.002
    self._trigger_activate_time = 0
    self._trigger_loop_flag = False
    self._trigger_loop_cond_var = asyncio.Condition()
    self._trigger_async_function = None
    self._task = None

  def SetCallbackAsyncFunction(self, coro):
    self._trigger_async_function = coro

  async def ActivateTimedTrigger(self, seconds_to_activate):
    activate_time = seconds_to_activate + time.time()
    self._trigger_activate_time = activate_time
    self._trigger_loop_cond_var.notify()

  async def StartTriggerHandlerTask(self, loop: asyncio.AbstractEventLoop):
    if self._task is not None:
      # try stop last one
      self._logger.info("last trigger handler exists, try stop...")
      self._trigger_loop_flag = False
      self._trigger_loop_cond_var.notify()
      await self._task
      self._logger.info("last trigger handler stopped")
    self._trigger_loop_flag = True
    self._task = loop.create_task(self._TriggerTaskLoop())
    self._logger.info("trigger handler created")

  async def _TriggerTaskLoop(self):
    print("in trigger task loop")
    while self._trigger_loop_flag:
      await self._trigger_loop_cond_var
      if self._trigger_loop_flag is False:
        break
      current_time = time.time()
      while current_time < self._trigger_activate_time:
        await asyncio.sleep(self._trigger_activate_time - current_time + self._trigger_pad_time)
      
      # done, do call back function
      if self._trigger_async_function:
        await self._trigger_async_function()


if __name__ == "__main__":
  async def CB():
    print("cb: {}".format(time.time()))
  async def MainTest():
    trig = AsyncTimedTrigger()
    trig.SetCallbackAsyncFunction(CB)
    await trig.StartTriggerHandlerTask(asyncio.get_event_loop())
    for i in range(2):
      print("current time: {}".format(time.time()))
      await trig.ActivateTimedTrigger(0.5)
      await time.sleep(2)
  asyncio.run(MainTest())