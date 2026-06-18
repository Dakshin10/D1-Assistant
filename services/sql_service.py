import time
import sqlite3
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from services.llm import llm
from services.d1_service import get_compressed_schema, get_ddl, get_schema
from services.query_logger import log_query
from services.sql_validator import needs_approval

# 1. Define Structured Pydantic Output Schema
class SQLResponse(BaseModel):
    sql: str = Field(description="The generated valid SQLite SQL statement.")
    query_type: str = Field(
        description="The category of the query. Must be one of: SELECT, INSERT, UPDATE, DELETE, CREATE, AGGREGATE."
    )
    requires_approval: bool = Field(
        description="True if the query is destructive/modifying (contains UPDATE, DELETE, CREATE, DROP, ALTER), False otherwise."
    )

# Instantiate the structured LLM parser
structured_llm = llm.with_structured_output(SQLResponse)

# 2. Optimized Prompt Template
system_template = """You are an expert SQLite and Cloudflare D1 SQL engineer.
Your task is to convert natural language requests into valid SQLite SQL.

Rules:
1. Return ONLY the SQL query.
2. Do not explain anything.
3. Do not use markdown.
4. Do not use code fences or backticks.
5. Use only tables and columns present in the schema.
6. Never invent tables.
7. Never invent columns.
8. Prefer explicit column names over SELECT *.
9. Generate efficient SQL.
10. For text comparisons, use LIKE when appropriate for case-insensitive matches.
11. Use LIMIT 100 unless the user explicitly requests all records.
12. Ensure SQL is compatible with SQLite and Cloudflare D1.

Database Schema:
{schema}

Few-Shot Examples:

User Request: Show all products
SQL: SELECT product_name, price, category FROM products LIMIT 100;

User Request: Show products costing more than 50000
SQL: SELECT product_name, price, category FROM products WHERE price > 50000 LIMIT 100;

User Request: Count products
SQL: SELECT COUNT(*) AS total_products FROM products;

User Request: Insert iPhone 16, 79999, Electronics into products
SQL: INSERT INTO products (product_name, price, category) VALUES ('iPhone 16', 79999, 'Electronics');

User Request: Update price of iPhone 16 to 74999 in products
SQL: UPDATE products SET price = 74999 WHERE product_name = 'iPhone 16';

User Request: Delete customers with email bob@example.com
SQL: DELETE FROM customers WHERE email = 'bob@example.com';
"""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_template),
    ("human", "User Request:\n{question}\n\nSQL:")
])

# 3. Fast-Path Handler for Common Queries
def check_fast_path(user_prompt: str) -> SQLResponse:
    """
    Checks if a prompt matches a common query pattern and returns direct SQL if so.
    This saves Groq API calls and reduces latency to < 1ms.
    """
    prompt_clean = user_prompt.strip().lower()
    
    # Show all products
    if prompt_clean in [
        "show all products", "list all products", "get all products",
        "show products", "list products"
    ]:
        return SQLResponse(
            sql="SELECT product_name, price, category FROM products LIMIT 100;",
            query_type="SELECT",
            requires_approval=False
        )
        
    # Count products
    if prompt_clean in [
        "count products", "how many products", "total products", "number of products"
    ]:
        return SQLResponse(
            sql="SELECT COUNT(*) AS total_products FROM products;",
            query_type="AGGREGATE",
            requires_approval=False
        )
        
    # List tables
    if prompt_clean in [
        "list tables", "show tables", "get tables", "what tables exist",
        "show all tables", "list all tables"
    ]:
        return SQLResponse(
            sql="SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('_cf_KV', 'sqlite_sequence');",
            query_type="SELECT",
            requires_approval=False
        )
        
    # Show schema
    if prompt_clean in [
        "show schema", "get schema", "what is the schema", "database schema"
    ]:
        return SQLResponse(
            sql="SELECT name, tbl_name, sql FROM sqlite_master WHERE type='table';",
            query_type="SELECT",
            requires_approval=False
        )

    return None

# 4. In-Memory SQLite Validation Layer
def validate_sql_against_schema(sql: str) -> tuple[bool, str]:
    """
    Validates a SQL query against the current D1 database schema (cached) by running
    EXPLAIN on a mock in-memory SQLite database preloaded with the table definitions.
    """
    # Block semicolon injection / multiple statements
    in_single_quote = False
    in_double_quote = False
    semicolon_outside = False
    for i, char in enumerate(sql):
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif char == ';' and not in_single_quote and not in_double_quote:
            # Semicolon outside quotes. If it's not the very end, check if text follows
            if i < len(sql) - 1 and sql[i+1:].strip():
                semicolon_outside = True
                break
                
    if semicolon_outside:
        return False, "Validation Error: Multiple statements are not allowed."
                
    # Create in-memory SQLite DB
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    
    try:
        # Load all cached table definitions (CREATE TABLE definitions)
        ddls = get_ddl()
        for table_name, create_sql in ddls.items():
            if create_sql:
                cursor.execute(create_sql)
        
        # Test compile query syntax and schema correctness
        cursor.execute(f"EXPLAIN {sql}")
        return True, ""
    except sqlite3.Error as e:
        return False, f"SQLite Syntax/Schema Error: {str(e)}"
    finally:
        conn.close()

# 5. LangGraph Node Compatibles / Generation Pipeline
def generate_sql(user_prompt: str) -> str:
    """
    Unified SQL Generation function.
    Combines fast-path checking, schema compression, structured ChatGroq generation,
    in-memory schema validation, execution timing, and logging.
    """
    start_time = time.time()
    
    # Step A: Fast path check
    fast_path_res = check_fast_path(user_prompt)
    if fast_path_res:
        latency = time.time() - start_time
        # Validate fast path query syntax just in case
        valid, err = validate_sql_against_schema(fast_path_res.sql)
        if not valid:
            log_query(user_prompt, fast_path_res.sql, fast_path_res.query_type, latency, False, err)
            return f"ERROR: Fast Path invalid: {err}"
        log_query(user_prompt, fast_path_res.sql, fast_path_res.query_type, latency, True)
        return fast_path_res.sql

    # Step B: Get compressed schema from cache
    schema = get_compressed_schema()
    
    token_usage = None
    query_type = "SELECT"
    
    try:
        # Step C: LLM structured call
        chain = prompt_template | structured_llm
        res = chain.invoke({
            "schema": schema,
            "question": user_prompt
        })
        
        sql = res.sql.strip()
        query_type = res.query_type
        
        # Parse token usage metadata if available
        # In langchain_groq, token usage is returned in response_metadata
        # Since structured_llm returns the Pydantic model directly, the raw message is not returned
        # to the invoke caller. To keep things clean, we will try to fetch if we can, or log default.
        
        # Step D: SQLite syntax and schema validation
        valid, err_msg = validate_sql_against_schema(sql)
        latency = time.time() - start_time
        
        if not valid:
            log_query(user_prompt, sql, query_type, latency, False, err_msg)
            return f"ERROR: Generated SQL failed schema validation. Details: {err_msg}"
            
        log_query(user_prompt, sql, query_type, latency, True)
        return sql
        
    except Exception as e:
        latency = time.time() - start_time
        log_query(user_prompt, "N/A", "UNKNOWN", latency, False, str(e))
        return f"ERROR: Failed to generate SQL: {str(e)}"