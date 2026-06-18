from services.grok_service import ask_llm
from services.d1_service import get_schema


def generate_delete_sql(user_prompt):

    schema = get_schema()

    prompt = f"""
You are a SQLite DELETE statement generator.

Database Schema:

{schema}

Rules:
1. Generate ONLY DELETE SQL.
2. Return ONLY SQL.
3. No markdown.
4. No explanations.

Examples:

User:
Delete all employees

Output:
DELETE FROM employees;

User:
Delete employees in HR

Output:
DELETE FROM employees
WHERE department = 'HR';

User Request:
{user_prompt}
"""

    return ask_llm(prompt)