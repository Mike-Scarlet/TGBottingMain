import asyncio

async def waiter(event):
    print('waiting for it ...')
    await event.wait()
    print('... got it!')

async def main():
    # Create an Event object.
    event = asyncio.Event()

    # Spawn a Task to wait until 'event' is set.
    waiter_task = asyncio.create_task(waiter(event))

    # Sleep for 1 second and set the event.
    await asyncio.sleep(1)
    event.set()

    waiter_task2 = asyncio.create_task(waiter(event))

    # Wait until the waiter task is finished.
    await waiter_task
    await waiter_task2

asyncio.run(main())