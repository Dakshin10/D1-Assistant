import sqlite3
import re

DB_NAME = "natural.db"


def execute_query(sql):

    try:

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(sql)

        # If it's a DELETE statement, check if table is empty to reset autoincrement sequence
        match = re.search(r'(?i)\bDELETE\s+FROM\s+["`\[]?(\w+)["`\]]?', sql)
        if match:
            table_name = match.group(1)
            try:
                cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                count = cursor.fetchone()[0]
                if count == 0:
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", (table_name,))
            except Exception:
                pass

        if sql.strip().upper().startswith("SELECT"):

            result = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            conn.close()

            return {
                "success": True,
                "result": result,
                "columns": columns
            }

        conn.commit()

        conn.close()

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

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
    """)

    tables = cursor.fetchall()

    schema_text = ""

    for table in tables:

        table_name = table[0]

        schema_text += f"\nTable: {table_name}\n"

        cursor.execute(
            f"PRAGMA table_info({table_name})"
        )

        columns = cursor.fetchall()

        for column in columns:

            schema_text += (
                f"- {column[1]} ({column[2]})\n"
            )

    conn.close()

    return schema_text


def get_tables():

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
    """)

    tables = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return tables


def get_table_data(table_name):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT * FROM {table_name}"
    )

    rows = cursor.fetchall()

    columns = [
        description[0]
        for description in cursor.description
    ]

    conn.close()

    return rows, columns