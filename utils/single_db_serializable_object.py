
from SQLiteWrapper import *

class SingleDBSerializableObject:
  def __init__(self, path:str=None, table_structure:SQLDatabase=None) -> None:
    self.db_path = None
    self.db_table_structure = None

    self._conn = None
    self._op = None

  def SetPath(self, path: str):
    self.db_path = path

  def SetTableStructure(self, structure: SQLDatabase):
    self.db_table_structure = structure

  def InitiateDB(self):
    self._conn = SQLite3Connector(
      self.db_path,
      self.db_table_structure
    )
    self._conn.Connect(do_check=False)
    self._conn.TableValidation()
    self._op = SQLite3Operator(self._conn)