import subprocess
import json
import time

DB_NAME = "minor-testdb"

class SchemaCache:
    """
    In-memory schema cache to store detailed schema descriptions,
    compressed schema definitions, list of tables, and DDL instructions.
    """
    def __init__(self, ttl=300):
        self.ttl = ttl
        self._schema_text = None
        self._compressed_schema = None
        self._tables = None
        self._table_ddl = None
        self._last_fetched = 0

    def is_expired(self):
        if self._last_fetched == 0:
            return True
        return (time.time() - self._last_fetched) > self.ttl

    def get_data(self, force=False):
        if force or self.is_expired() or self._schema_text is None:
            self.refresh()
        return {
            "schema_text": self._schema_text,
            "compressed_schema": self._compressed_schema,
            "tables": self._tables,
            "table_ddl": self._table_ddl
        }

    def refresh(self):
        # Fetch tables and their sql definitions from sqlite_master
        sql_tables = """
        SELECT name, sql
        FROM sqlite_master
        WHERE type='table'
        """
        # Call the underlying execute_query directly to avoid recursion
        result = _raw_execute_query(sql_tables)
        if not result["success"]:
            if self._schema_text is None:
                self._schema_text = ""
                self._compressed_schema = ""
                self._tables = []
                self._table_ddl = {}
            return
        
        tables = []
        ddl = {}
        schema_text = ""
        compressed_parts = []
        
        for row in result["result"]:
            table_name = row["name"]
            if table_name in ["_cf_KV", "sqlite_sequence"]:
                continue
            tables.append(table_name)
            ddl[table_name] = row["sql"] if row["sql"] else f"CREATE TABLE {table_name}"
            
            schema_text += f"\nTable: {table_name}\n"
            
            pragma_sql = f"PRAGMA table_info({table_name})"
            pragma_result = _raw_execute_query(pragma_sql)
            
            cols = []
            if pragma_result["success"]:
                for column in pragma_result["result"]:
                    schema_text += f"- {column['name']} ({column['type']})\n"
                    cols.append(column['name'])
            
            compressed_parts.append(f"{table_name}({', '.join(cols)})")
            
        self._tables = tables
        self._table_ddl = ddl
        self._schema_text = schema_text
        self._compressed_schema = "\n".join(compressed_parts)
        self._last_fetched = time.time()

    def invalidate(self):
        self._schema_text = None
        self._compressed_schema = None
        self._tables = None
        self._table_ddl = None
        self._last_fetched = 0

schema_cache = SchemaCache()

def _raw_execute_query(sql):
    """Internal helper to execute a query without any cache check/invalidation hooks."""
    try:
        sql_clean = " ".join(sql.split())
        cmd = f'npx wrangler d1 execute {DB_NAME} --remote --command="{sql_clean}" --json'

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=True,
            encoding="utf-8"
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr
            }

        data = json.loads(result.stdout)

        if not data:
            return {
                "success": False,
                "error": "No response from D1"
            }

        d1_response = data[0]

        if sql.strip().upper().startswith(("SELECT", "PRAGMA")):
            rows = d1_response.get("results", [])
            columns = []
            if rows:
                columns = list(rows[0].keys())
            return {
                "success": True,
                "result": rows,
                "columns": columns
            }

        return {
            "success": True,
            "result": "Query executed successfully."
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def execute_query(sql):
    # Execute query
    result = _raw_execute_query(sql)
    
    # Invalidate cache if successful and contains schema modifications
    if result["success"]:
        sql_upper = sql.strip().upper()
        if sql_upper.startswith(("CREATE", "DROP", "ALTER")):
            schema_cache.invalidate()
            
    return result

def get_schema():
    return schema_cache.get_data()["schema_text"]

def get_compressed_schema():
    return schema_cache.get_data()["compressed_schema"]

def get_tables():
    return schema_cache.get_data()["tables"]

def get_ddl():
    return schema_cache.get_data()["table_ddl"]

def get_table_data(table_name):
    sql = f"SELECT * FROM {table_name}"
    result = execute_query(sql)

    if not result["success"]:
        return [], []

    rows = result["result"]
    if not rows:
        return [], []

    columns = list(rows[0].keys())
    data = [list(row.values()) for row in rows]
    return data, columns