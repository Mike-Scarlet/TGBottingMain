
import time

class PeriodicContent:
  def __init__(self) -> None:
    self.time = None
    self.count = None

class PeriodicRestriction:
  def __init__(self) -> None:
    self._period = 10.0  # in seconds
    self._count = 10
    self._inlier_list = []

  def SetPeriod(self, period):
    self._period = period

  def SetRestrictCount(self, count):
    self._count = count

  def UpdateInnerCountent(self):
    current_time = time.time()

  async def AddCountByNow(self, count):
    pass