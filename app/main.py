from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from typing import List, Optional
from pathlib import Path
import asyncio
import json
import logging

print("🚀 MAIN.PY STARTING...")

# -------------------------------
# SAFE IMPORTS
# -------------------------------
try:
    from app.core.security import verify_api_key

    from app.utils import (
        save_uploaded_file_temp,
        clone_github_repo_temp,
        get_python_files,
        get_redis_connection,
        get_pg_connection,
    )

    from app.static_analysis.structure_extractor import parse_file, extract_structure
    from app.static_analysis.static_analysis import analyze_file, calculate_confidence

    from app.llm.review_llm import run_llm_review
    from app.llm.refactor_llm import run_llm_refactor
    from app.llm.doc_llm import run_llm_docstrings
    from app.llm.readme_llm import run_llm_readme

    from app.models import LLMReview, RefactorResult, DocResult

    from psycopg2.extras import Json
    from pydantic import ValidationError

    print("✅ IMPORTS SUCCESS")

except Exception as e:
    print("❌ IMPORT ERROR:", e)
    raise e


# -------------------------------
# RATE LIMITING
# -------------------------------
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# -------------------------------
# LOGGING
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# APP INIT
# -------------------------------
app = FastAPI(title="Automated Code Review")

print("✅ FASTAPI CREATED")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": str(exc)})


# -------------------------------
# SAFE CONNECTIONS
# -------------------------------
def safe_redis():
    try:
        return get_redis_connection()
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
        return None


def safe_pg():
    try:
        return get_pg_connection()
    except Exception as e:
        logger.warning(f"Postgres not available: {e}")
        return None


# -------------------------------
# SAFE LLM WRAPPERS (NO CRASH)
# -------------------------------
def safe_llm_review(structure, analysis):
    try:
        result = run_llm_review(structure, analysis)
        if not result:
            return {"summary": "LLM returned empty", "issues": []}
        return result
    except Exception as e:
        logger.warning(f"LLM review failed: {e}")
        return {"summary": f"LLM error: {e}", "issues": []}


def safe_refactor(code, analysis):
    try:
        result = run_llm_refactor(code, analysis)
        if not result:
            return {"refactored_code": code, "diff": ""}
        return result
    except Exception as e:
        logger.warning(f"Refactor failed: {e}")
        return {"refactored_code": code, "diff": f"Error: {e}"}


def safe_docstrings(code):
    try:
        result = run_llm_docstrings(code)
        if not result:
            return {"documented_code": code}
        return result
    except Exception as e:
        logger.warning(f"Docstrings failed: {e}")
        return {"documented_code": code}


# -------------------------------
# ANALYSIS
# -------------------------------
def analyze_sync(file_path: Path):
    tree = parse_file(file_path)
    structure = extract_structure(tree)
    analysis = analyze_file(file_path)

    llm_review = safe_llm_review(structure, analysis)
    pre_conf = calculate_confidence(analysis)

    code = file_path.read_text(encoding="utf-8")

    refactor = safe_refactor(code, analysis)
    doc = safe_docstrings(refactor["refactored_code"])

    return {
        "file": str(file_path),
        "structure": structure,
        "analysis": analysis,
        "llm_review": llm_review,
        "pre_confidence": pre_conf,
        "refactored_code": refactor["refactored_code"],
        "diff": refactor["diff"],
        "documented_code": doc["documented_code"],
        "issues": analysis.get("issues", []),
    }


async def analyze_async(file_path: Path):
    return await asyncio.to_thread(analyze_sync, file_path)


# -------------------------------
# UPLOAD ENDPOINT
# -------------------------------
@app.post("/upload-code/", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def upload_code(
    request: Request,
    files: List[UploadFile] = File(None),
    repo_url: Optional[str] = Form(None),
):
    logger.info("Upload endpoint triggered")

    tasks = []
    MAX_FILE_SIZE = 2 * 1024 * 1024

    # ---------------- FILES ----------------
    if files:
        for file in files:
            content = await file.read()

            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")

            file.file.seek(0)

            file_path, _ = save_uploaded_file_temp(file)

            for py in get_python_files(file_path.parent):
                tasks.append(analyze_async(py))

    # ---------------- REPO ----------------
    if repo_url:
        try:
            repo_path, _ = clone_github_repo_temp(repo_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Repo clone failed: {e}")

        for py in get_python_files(repo_path):
            tasks.append(analyze_async(py))

    if not tasks:
        raise HTTPException(status_code=400, detail="No valid input provided")

    results = await asyncio.gather(*tasks)

    overall_pre = sum(r["pre_confidence"] for r in results) / len(results)

    # ---------------- REDIS ----------------
    r = safe_redis()
    if r:
        try:
            r.set("latest_session", json.dumps({"files": len(results)}))
        except Exception:
            pass

    # ---------------- POSTGRES ----------------
    conn = safe_pg()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO public.analysis_runs
                (repo, files, overall_pre_confidence)
                VALUES (%s, %s, %s)
                """,
                (
                    repo_url if repo_url else "uploaded_files",
                    len(results),
                    round(overall_pre, 2),
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Postgres insert failed: {e}")

    return {
        "overall_pre_confidence": round(overall_pre, 2),
        "files": results,
    }
