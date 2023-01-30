
import asyncio

class C:
  def __init__(self) -> None:
    pass

  def F(self):
    pass

  async def C(self):
    pass

c = C()
print(asyncio.iscoroutinefunction(c.F))
print(asyncio.iscoroutinefunction(c.C))