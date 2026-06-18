import subprocess
import json

DB_NAME = "minor-testdb"


def execute_query(sql):

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


def get_schema():

    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """

    result = execute_query(sql)

    if not result["success"]:
        return result["error"]

    schema_text = ""

    for table in result["result"]:

        table_name = table["name"]

        if table_name in ["_cf_KV", "sqlite_sequence"]:
            continue

        schema_text += f"\nTable: {table_name}\n"

        pragma_sql = f"PRAGMA table_info({table_name})"

        pragma_result = execute_query(pragma_sql)

        if pragma_result["success"]:

            for column in pragma_result["result"]:

                schema_text += (
                    f"- {column['name']} ({column['type']})\n"
                )

    return schema_text


def get_tables():

    sql = """
    SELECT name
    FROM sqlite_master
    WHERE type='table'
    """

    result = execute_query(sql)

    print("\n===== GET TABLES =====")
    print(result)
    print("======================\n")

    if not result["success"]:
        return []

    return [
        row["name"]
        for row in result["result"]
        if row["name"] not in ["_cf_KV", "sqlite_sequence"]
    ]


def get_table_data(table_name):

    sql = f"SELECT * FROM {table_name}"

    result = execute_query(sql)

    if not result["success"]:
        return [], []

    rows = result["result"]

    if not rows:
        return [], []

    columns = list(rows[0].keys())

    data = [
        list(row.values())
        for row in rows
    ]

    return data, columns