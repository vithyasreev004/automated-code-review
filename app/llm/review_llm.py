import os, time, requests, json, re
from dotenv import load_dotenv
from threading import Semaphore

load_dotenv()
GROQ_API_KEY = os.getenv("API_KEY")

URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
MODEL = "llama-3.3-70b-versatile"
LLM_SEMAPHORE = Semaphore(2)
MAX_RETRIES = 3
BACKOFF_SECONDS = 5

def run_llm_review(structure: dict, analysis: dict) -> dict:
    prompt = f"""
You are a senior Python software engineer performing a strict code review.
Return JSON ONLY with keys:
- summary (string)
- issues (list of {{category, severity, line, suggestion}})
- confidence (float)

AST:{structure}
Static Analysis:{analysis}
"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role":"system","content":"You are a strict code reviewer."},
            {"role":"user","content":prompt}
        ],
        "temperature":0.2,
        "max_tokens":600
    }

    for attempt in range(1, MAX_RETRIES+1):
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
                    if "issues" not in parsed:
                        parsed["issues"] = []
                    if "confidence" not in parsed:
                        parsed["confidence"] = 0.0
                    if "summary" not in parsed:
                        parsed["summary"] = "No summary provided"
                    return parsed
                except Exception:
                    return {"summary":"Invalid JSON from LLM","issues":[],"confidence":0}
            else:
                return {"summary":"No JSON found in LLM output","issues":[],"confidence":0}

        if response.status_code == 429:
            if attempt == MAX_RETRIES:
                return {"summary":"LLM rate limit exceeded","issues":[],"confidence":0}
            time.sleep(BACKOFF_SECONDS*attempt)
        else:
            return {"summary":f"LLM error {response.status_code}","issues":[],"confidence":0}
