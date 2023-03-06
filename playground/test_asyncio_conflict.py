
import asyncio

async def inner():
  await asyncio.sleep(1)

async def af():
  print("begin")
  await inner()
  print("done")

async def main():
  loop = asyncio.get_event_loop()
  tasks = []
  for _ in range(10):
    tasks.append(loop.create_task(af()))
  for i in range(10):
    await tasks[i]

asyncio.run(main())