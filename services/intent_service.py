from services.grok_service import ask_llm


def detect_intent(user_prompt):

    prompt = f"""
You are an intent classifier.

Possible intents:

- create_table
- insert_data
- query_data
- delete_data
- update_data

Examples:

User: Create a table called employees
Intent: create_table

User: Add John to employees
Intent: insert_data

User: Show all employees
Intent: query_data

User: Delete all employees
Intent: delete_data

User: Remove employee John
Intent: delete_data

User: Change John's salary to 60000
Intent: update_data

Return ONLY the intent.

User:
{user_prompt}
"""

    return ask_llm(prompt).strip().lower()