
__all__ = [
  "PeriodicRestriction"
]

import time
import typing
import asyncio

class PeriodicContent:
  def __init__(self) -> None:
    self.time = None
    self.count = None

class PeriodicRestriction:
  _inlier_list = typing.List[PeriodicContent]
  def __init__(self) -> None:
    self._period = 10.0  # in seconds
    self._count_thresh = 10
    self._inlier_list = []
    self._latch_count = 0

  def SetPeriod(self, period):
    self._period = period

  def SetRestrictCount(self, count):
    self._count_thresh = count

  def UpdateInnerCountent(self):
    current_time = time.time()
    while len(self._inlier_list) > 0 and current_time - self._inlier_list[0].time > self._period:
      self._latch_count -= self._inlier_list[0].count
      del self._inlier_list[0]

  async def WaitTillNextTimeAync(self):
    if len(self._inlier_list) > 0:
      next_expire_time = self._inlier_list[0].time + self._period
      sleep_time = next_expire_time - time.time()
      if sleep_time > 0:
        await asyncio.sleep(sleep_time)

  async def AddCountByNowAsyncPreCheck(self, count):
    if self._count_thresh >= 0:
      while self._latch_count + count > self._count_thresh:
        if count > self._count_thresh and self._latch_count == 0:
          break  # stop, no wait
        await self.WaitTillNextTimeAync()
        self.UpdateInnerCountent()
    add_time = time.time()
    content = PeriodicContent()
    content.time = add_time
    content.count = count
    self._inlier_list.append(content)
    self._latch_count += count

async def test_main():
  restrict = PeriodicRestriction()
  restrict.SetPeriod(3)
  restrict.SetRestrictCount(6)
  for i in range(6):  
    print(i, time.time())
    await restrict.AddCountByNowAsyncPreCheck(10)
    await asyncio.sleep(0.1)
  for i in range(15):  
    print(i, time.time())
    await restrict.AddCountByNowAsyncPreCheck(1)
    print("added")

if __name__ == "__main__":
  asyncio.run(test_main())