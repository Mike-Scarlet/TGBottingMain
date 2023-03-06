
import telegram
import asyncio

async def TGFuncWrap(coro, retry_times=3):
  """Return value:
    [status, coro ret / exception / None]
    if status is true, second is coro ret
    if status is false
      if second is None, means network issue
      otherwise specified exception is returned
  """
  for retry in range(retry_times):
    try:
      ret = await coro
      return True, ret
    except (telegram.error.NetworkError, telegram.error.TimedOut) as e:
      await asyncio.sleep(retry * 2.5)
      continue
    except Exception as e:
      return False, e
  return False, None