import os
import json
import time

LOG_FILE = "logs/query_log.jsonl"

def log_query(question, sql, query_type, latency_seconds, success, error_message=None, token_usage=None):
    """
    Appends query metadata to a JSONL log file for analytics and performance tracking.
    """
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    log_entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "sql": sql,
        "query_type": query_type,
        "latency_seconds": round(latency_seconds, 4),
        "success": success,
        "error_message": error_message,
        "token_usage": token_usage or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
    
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Failed to write query log: {e}")
