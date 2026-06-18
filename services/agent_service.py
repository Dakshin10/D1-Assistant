from langchain.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from services.llm import llm
from services.d1_service import get_schema as d1_get_schema, get_tables, execute_query
from services.sql_validator import needs_approval

@tool
def get_schema() -> str:
    """Retrieve the database schema, including all table names and column definitions."""
    return d1_get_schema()

@tool
def list_tables() -> list:
    """Retrieve a list of all table names currently in the database."""
    return get_tables()

@tool
def execute_sql(sql: str) -> str:
    """
    Execute a SELECT or PRAGMA SQLite query against the database and return the results.
    Do NOT call this tool for UPDATE, INSERT, DELETE, DROP, ALTER, or CREATE queries,
    as they require human approval and cannot be executed automatically.
    """
    if needs_approval(sql):
        return "ERROR: Query contains destructive commands (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER) and cannot be executed automatically. You must return the generated SQL query to the user for manual approval."
    
    result = execute_query(sql)
    if result.get("success"):
        return str(result.get("result"))
    else:
        return f"ERROR: {result.get('error')}"

tools = [get_schema, list_tables, execute_sql]

system_prompt = """You are a SQLite assistant agent.
Your primary job is to generate a SQLite query matching the user's natural language request.

You have access to the database tools:
- list_tables: to see all tables.
- get_schema: to get table definitions and column details.
- execute_sql: to run SELECT/read queries if you need to verify data contents.

Rules:
1. First, check the tables or schema to see what structure exists.
2. Formulate a valid SQLite SQL statement.
3. If the user request is a retrieval/read operation (SELECT), you can execute the query using `execute_sql` to confirm it is valid, but your FINAL answer to the user should be ONLY the generated SQL query statement.
4. If the user request is a CREATE, INSERT, UPDATE, DELETE, DROP, or ALTER statement, you MUST NOT execute it. You should generate the SQL query and output it as your FINAL answer to the user.
5. Your final response should contain ONLY the generated SQL query. Do not wrap it in markdown codeblocks (do not use ```sql ... ```). No explanations, no comments, no intro/outro text.
6. If the request is invalid, cannot be translated to SQLite, or references tables/columns that do not exist, your final answer should be: "ERROR: Invalid Request".
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the tool calling agent
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

def generate_sql_via_agent(user_prompt):
    """
    Runs the LangChain SQL Agent to understand the request, inspect the schema,
    and return the generated SQL statement.
    """
    try:
        res = agent_executor.invoke({
            "input": user_prompt,
            "chat_history": []
        })
        sql = res.get("output", "").strip()
        
        # Clean markdown code blocks if the model generated them despite instructions
        if sql.startswith("```"):
            lines = sql.splitlines()
            if len(lines) >= 2:
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                sql = "\n".join(lines).strip()
        return sql
    except Exception as e:
        return f"ERROR: Agent failed: {str(e)}"
