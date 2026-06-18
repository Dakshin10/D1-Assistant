import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

# Get GROQ_API_KEY from environment
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables or .env file.")

# Reusable ChatGroq LLM instance
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    groq_api_key=api_key,
    temperature=0,
    max_tokens=300,
    model_kwargs={"top_p": 1.0}
)
