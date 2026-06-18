from services.grok_service import ask_llm
from services.d1_service import get_schema


def generate_insert_sql(user_prompt):

    schema = get_schema()

    prompt = f"""
You are an expert SQLite SQL generator.

Database Schema:

{schema}

Task:
Generate a valid SQLite INSERT statement.

Rules:
1. Return ONLY SQL.
2. Do NOT explain.
3. Do NOT use markdown.
4. Do NOT wrap SQL inside quotes.
5. Do NOT generate SELECT statements.
6. Output must start with INSERT INTO.

Example:

User:
Insert into products:
iPhone 16, 79999, Electronics

Output:
INSERT INTO products (product_name, price, category)
VALUES ('iPhone 16', 79999, 'Electronics');

User Request:
{user_prompt}
"""

    sql = ask_llm(prompt)

    return sql.strip()