import requests, json, re
from app.llm.review_llm import URL, HEADERS, MODEL, LLM_SEMAPHORE

def run_llm_docstrings(refactored_code: str) -> dict:
    prompt = f"""
Add comprehensive Google-style docstrings and inline comments to the following Python code.
Return JSON ONLY with keys:
- documented_code (string)
- issues (list of {{category, severity, line, suggestion}}). If none, return []
Code:
{refactored_code}
"""
    payload = {
        "model": MODEL,
        "messages":[
            {"role":"system","content":"You are a documentation assistant."},
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

        # 🔹 Extract JSON block safely
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if "documented_code" not in parsed:
                    parsed["documented_code"] = refactored_code
                if "issues" not in parsed:
                    parsed["issues"] = []
                return parsed
            except Exception:
                return {"documented_code": f'"""Stub (invalid JSON)"""\n{refactored_code}', "issues":[]}
        else:
            return {"documented_code": f'"""Stub (no JSON found)"""\n{refactored_code}', "issues":[]}

    return {"documented_code": f'"""Stub (no choices returned)"""\n{refactored_code}', "issues":[]}
