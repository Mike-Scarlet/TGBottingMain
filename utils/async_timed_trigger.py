
import time
import asyncio
import logging

class AsyncTimedTrigger:
  def __init__(self) -> None:
    self._logger = logging.getLogger("AsyncTimedTrigger")
    self._task_access_lock = asyncio.Lock()
    self._trigger_pad_time = 0.002
    self._trigger_activate_time = 0
    self._trigger_loop_flag = False
    self._trigger_loop_cond_var = asyncio.Condition()
    self._trigger_async_function = None

    self._callback_last_time = time.time()
    self._task = None

  def SetCallbackAsyncFunction(self, coro):
    self._trigger_async_function = coro

  async def ActivateTimedTrigger(self, seconds_to_activate):
    activate_time = seconds_to_activate + time.time()
    self._trigger_activate_time = activate_time
    async with self._trigger_loop_cond_var:
      self._trigger_loop_cond_var.notify()

  async def StartTriggerHandlerTask(self, loop: asyncio.AbstractEventLoop):
    async with self._task_access_lock:
      if self._task is not None:
        self._task_access_lock.release()
        await self.StopTriggerHandlerTask()
        await self._task_access_lock.acquire()
      self._trigger_loop_flag = True
      self._task = loop.create_task(self._TriggerTaskLoop())
      self._logger.info("trigger handler created")
      await asyncio.sleep(0.1)

  async def StopTriggerHandlerTask(self):
    async with self._task_access_lock:
      if self._task is None:
        return
      # try stop last one
      self._logger.info("last trigger handler exists, try stop...")
      self._trigger_loop_flag = False
      async with self._trigger_loop_cond_var:
        self._trigger_loop_cond_var.notify()
      await self._task
      self._task = None
      self._logger.info("last trigger handler stopped")

  async def _TriggerTaskLoop(self):
    self._logger.info("in trigger task loop")
    while self._trigger_loop_flag:
      async with self._trigger_loop_cond_var:
        await self._trigger_loop_cond_var.wait()
      if self._trigger_loop_flag is False:
        break
      current_time = time.time()
      while current_time < self._trigger_activate_time:
        # print("sleep: {}".format(self._trigger_activate_time - current_time + self._trigger_pad_time))
        await asyncio.sleep(self._trigger_activate_time - current_time + self._trigger_pad_time)
        current_time = time.time()
      
      # done, do call back function
      if self._trigger_async_function:
        try:
          await self._trigger_async_function()
        except:
          pass
    self._logger.info("trigger task loop exited")


if __name__ == "__main__":
  from python_general_lib.environment_setup.logging_setup import *
  async def CB():
    print("cb: {}".format(time.time()))
  async def MainTest():
    trig = AsyncTimedTrigger()
    trig.SetCallbackAsyncFunction(CB)
    await trig.StartTriggerHandlerTask(asyncio.get_event_loop())
    # for i in range(2):
    #   print("current time: {}".format(time.time()))
    #   await trig.ActivateTimedTrigger(0.5)
    #   await asyncio.sleep(2)
    for i in range(3):
      print("current time: {}".format(time.time()))
      await trig.ActivateTimedTrigger(2.0)
      await asyncio.sleep(0.5)
    await asyncio.sleep(3.0)
    # for i in range(2):
    #   print("current time: {}".format(time.time()))
    #   await trig.ActivateTimedTrigger(0.5)
    #   await asyncio.sleep(2)
    await trig.StopTriggerHandlerTask()

    await trig.StartTriggerHandlerTask(asyncio.get_event_loop())
    await trig.StartTriggerHandlerTask(asyncio.get_event_loop())

    for i in range(2):
      print("current time: {}".format(time.time()))
      await trig.ActivateTimedTrigger(0.5)
      await asyncio.sleep(2)

    await trig.StopTriggerHandlerTask()
  asyncio.run(MainTest())