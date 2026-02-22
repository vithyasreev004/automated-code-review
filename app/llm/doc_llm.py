import requests
from .review_llm import URL, HEADERS, MODEL, LLM_SEMAPHORE

def run_llm_docstrings(refactored_code: str) -> str:
    prompt = f"""
Add comprehensive Google-style docstrings and inline comments to the following Python code:
{refactored_code}
Return ONLY the documented code.
"""
    payload = {"model": MODEL, "messages":[{"role":"system","content":"You are a documentation assistant."},{"role":"user","content":prompt}], "temperature":0.2, "max_tokens":800}
    with LLM_SEMAPHORE:
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    return response.json()["choices"][0]["message"]["content"]
