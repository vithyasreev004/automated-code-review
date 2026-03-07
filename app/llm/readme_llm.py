import requests, json
from .review_llm import URL, HEADERS, MODEL, LLM_SEMAPHORE

def run_llm_readme(results: list, overall_pre: float, overall_post: float) -> str:
    """
    Generate a README.md draft for the repository based on analysis results.
    """
    summary = {
        "overall_pre_confidence": overall_pre,
        "overall_post_confidence": overall_post,
        "files_analyzed": len(results),
        "issues_detected": sum(len(r["llm_review"].get("issues", [])) for r in results)
    }

    prompt = f"""
Generate a professional README.md for this repository.
Include:
- Project overview
- Installation instructions
- Usage examples
- Contribution guidelines
- Summary of code quality improvements

Repo Summary:
{summary}
"""

    payload = {
        "model": MODEL,
        "messages":[
            {"role":"system","content":"You are a documentation assistant."},
            {"role":"user","content":prompt}
        ],
        "temperature":0.3,
        "max_tokens":800
    }
    with LLM_SEMAPHORE:
        response = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    data = response.json()
    if "choices" in data and len(data["choices"]) > 0:
        return data["choices"][0]["message"]["content"]
    return "# README\n\nFailed to generate README."
