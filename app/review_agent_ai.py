import os
import requests
from dotenv import load_dotenv

# Load Groq API key
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY in .env file")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

MODEL = "llama-3.3-70b-versatile"

# Helper function
def run_agent(role_instruction, user_prompt):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": role_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.2
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.status_code} {response.text}"

# Sample code
sample_code = """
class Calculator:
    def add(self, a, b):
        return a + b

    def divide(self, a, b):
        return a / b
"""

# Review Agent
print("="*40)
print("AI CODE REVIEW OUTPUT")
print("="*40)
print(run_agent("You are a senior Python software engineer.",
                f"Review the following Python code:\n```python\n{sample_code}\n```"))

# Refactor Agent
print("\n" + "="*40)
print("AI CODE REFACTOR OUTPUT")
print("="*40)
print(run_agent("You are a senior Python software engineer.",
                f"Refactor the following Python code to improve readability, robustness, and handle edge cases:\n```python\n{sample_code}\n```"))

# Docstring Agent
print("\n" + "="*40)
print("AI CODE DOCSTRING OUTPUT")
print("="*40)
print(run_agent("You are a senior Python software engineer.",
                f"Add clear and concise Python docstrings to the following code:\n```python\n{sample_code}\n```"))
