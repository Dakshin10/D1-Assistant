from services.grok_service import ask_llm
from services.d1_service import get_schema


def generate_sql(user_prompt):

    schema = get_schema()

    prompt = f"""
You are a SQLite SQL generation engine.

Database Schema:

{schema}

Instructions:

1. Generate ONLY valid SQLite SQL.
2. Return ONLY SQL.
3. Never explain your answer.
4. Never use markdown.
5. Never invent tables.
6. Never invent columns.
7. Use only tables and columns from the schema.
8. If the user wants data inserted, generate INSERT statements.
9. If the user wants data retrieved, generate SELECT statements.
10. If the request is invalid, return:
ERROR: Invalid Request

Examples:

Schema:
Table: employees
- employee_name (TEXT)
- salary (REAL)
- department (TEXT)

User:
Insert into employees:
John, 50000, HR

Output:
INSERT INTO employees (
    employee_name,
    salary,
    department
)
VALUES (
    'John',
    50000,
    'HR'
);

User Request:
{user_prompt}
"""

    return ask_llm(prompt)


def generate_query_sql(user_prompt):

    schema = get_schema()

    prompt = f"""
You are an expert SQLite query generator.

Database Schema:

{schema}

Rules:
1. Generate ONLY a SELECT statement.
2. Use only existing tables and columns.
3. Return ONLY SQL.
4. No markdown.
5. No explanations.
6. Never generate INSERT, UPDATE, DELETE, DROP, ALTER or CREATE.
7. Always use the schema provided.

Examples:

User:
Show all employees

Output:
SELECT * FROM employees;

User:
Who works in HR?

Output:
SELECT employee_name
FROM employees
WHERE department = 'HR';

User Question:
{user_prompt}
"""

    return ask_llm(prompt)