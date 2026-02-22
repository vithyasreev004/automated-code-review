import requests
from .review_llm import URL, HEADERS, MODEL, LLM_SEMAPHORE

def run_llm_refactor(code: str, issues: dict) -> str:
    prompt = f"""
Refactor the following Python code to fix issues:
Issues: {issues}
Code:
{code}
Return ONLY the refactored code.
"""
    payload = {"model": MODEL, "messages":[{"role":"system","content":"You are a strict refactoring assistant."},{"role":"user","content":prompt}], "temperature":0.2, "max_tokens":800}
    with LLM_SEMAPHORE:
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    return response.json()["choices"][0]["message"]["content"]
