from services.grok_service import ask_llm
from services.d1_service import get_schema


def generate_update_sql(user_prompt):

    schema = get_schema()

    prompt = f"""
You are a SQLite UPDATE statement generator.

Database Schema:

{schema}

Rules:
1. Generate ONLY UPDATE SQL.
2. Return ONLY SQL.
3. No markdown.
4. No explanations.

User Request:
{user_prompt}
"""

    return ask_llm(prompt)