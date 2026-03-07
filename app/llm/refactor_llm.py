import requests, json
from .review_llm import URL, HEADERS, MODEL, LLM_SEMAPHORE

def run_llm_refactor(code: str, issues: dict) -> dict:
    prompt = f"""
Refactor the following Python code to fix issues.
Return JSON ONLY with keys:
- refactored_code (string)
- diff (unified diff format showing changes)

Code:
{code}
Issues:
{issues}
"""
    payload = {
        "model": MODEL,
        "messages":[
            {"role":"system","content":"You are a strict refactoring assistant."},
            {"role":"user","content":prompt}
        ],
        "temperature":0.2,
        "max_tokens":800
    }
    with LLM_SEMAPHORE:
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    data = response.json()
    if "choices" in data and len(data["choices"]) > 0:
        content = data["choices"][0]["message"]["content"]
        try:
            cleaned = content.strip().strip("`")
            parsed = json.loads(cleaned)
            if "refactored_code" not in parsed:
                parsed["refactored_code"] = content
            if "diff" not in parsed:
                parsed["diff"] = ""
            return parsed
        except Exception:
            return {"refactored_code":content,"diff":""}
    return {"refactored_code":"","diff":""}
