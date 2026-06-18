from services.grok_service import ask_llm


def generate_create_sql(user_prompt):

    prompt = f"""
You are a SQLite schema designer.

Rules:
1. Generate ONLY CREATE TABLE SQL.
2. Always include:
   id INTEGER PRIMARY KEY AUTOINCREMENT
3. Return only SQL.
4. No markdown.
5. No explanations.

User Request:
{user_prompt}
"""

    return ask_llm(prompt)