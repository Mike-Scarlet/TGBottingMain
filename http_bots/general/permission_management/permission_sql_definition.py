

from SQLiteWrapper import *

permission_db_initiate_dict = {
  "Messages": {
    "field_definition": {
      # > MAIN FIELDS
      "user_id": "INTEGER UNIQUE NOT NULL",
      "permission_value": "INTEGER",
    },
    "primary_keys": "user_id"
  }
}

permission_db_table_structure = SQLDatabase.CreateFromDict(permission_db_initiate_dict)