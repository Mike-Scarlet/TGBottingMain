
from SQLiteWrapper import *
import asyncio

class SingleChatMessageManager:
  """ just do message management """
  def __init__(self, db_path=None) -> None:
    self._db_path = db_path
    self._db_access_lock = asyncio.Lock()

  """ initiate interfaces """  
  def SetDBPath(self, db_path):
    self._db_path = db_path

  async def InitiateDB(self):
    with self._db_access_lock:
      pass

  """ insert interfaces """  
  async def InsertMessage(self, message):
    pass

  """ query interfaces """
