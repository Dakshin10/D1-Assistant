from services.grok_service import ask_llm
from services.d1_service import get_schema


def generate_query_sql(user_prompt):

    schema = get_schema()

    prompt = f"""
You are a SQLite query generator.

Database Schema:

{schema}

Rules:
1. Generate ONLY SELECT SQL.
2. Use only tables from schema.
3. Use only columns from schema.
4. Return only SQL.
5. No markdown.
6. No explanations.

User Question:
{user_prompt}
"""

    return ask_llm(prompt)