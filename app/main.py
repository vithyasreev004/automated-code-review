from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from typing import List, Optional
from pathlib import Path
import asyncio
import json
import logging

print("🚀 MAIN.PY STARTING...")

# -------------------------------
# Safe Imports
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

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# App Init
# -------------------------------
app = FastAPI(title="Automated Code Review")

print("✅ FASTAPI CREATED")

# -------------------------------
# Rate Limiter
# -------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})

# -------------------------------
# Global Error Handler
# -------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": str(exc)})

# -------------------------------
# Safe Helpers
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
# LLM Wrappers with Timeout
# -------------------------------
async def llm_with_timeout(func, *args):
    try:
        return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=20)
    except Exception as e:
        return {"error": str(e)}

def safe_llm_review(structure, analysis):
    try:
        raw = run_llm_review(structure, analysis)
        return LLMReview.parse_obj(raw).dict()
    except Exception as e:
        return {"summary": f"LLM error: {e}"}

def safe_refactor(code, analysis):
    try:
        raw = run_llm_refactor(code, analysis)
        return RefactorResult.parse_obj(raw).dict()
    except Exception as e:
        return {"refactored_code": code, "diff": f"Error: {e}"}

def safe_docstrings(code):
    try:
        raw = run_llm_docstrings(code)
        return DocResult.parse_obj(raw).dict()
    except Exception as e:
        return {"documented_code": code}

# -------------------------------
# Core Analysis
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
        "analysis": analysis,
        "llm_review": llm_review,
        "pre_confidence": pre_conf,
        "refactored_code": refactor["refactored_code"],
        "diff": refactor["diff"],
        "documented_code": doc["documented_code"],
    }

async def analyze_async(file_path: Path):
    return await asyncio.to_thread(analyze_sync, file_path)

# -------------------------------
# Upload Endpoint
# -------------------------------
@app.post("/upload-code/", dependencies=[Depends(verify_api_key)])
@limiter.limit("5/minute")
async def upload_code(
    request: Request,
    files: List[UploadFile] = File(None),
    repo_url: Optional[str] = Form(None),
):
    logger.info("Upload triggered")

    tasks = []
    MAX_FILE_SIZE = 2 * 1024 * 1024

    # Files
    if files:
        for file in files:
            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")

            file.file.seek(0)
            file_path, _ = save_uploaded_file_temp(file)

            for py in get_python_files(file_path.parent):
                tasks.append(analyze_async(py))

    # Repo
    if repo_url:
        try:
            repo_path, _ = clone_github_repo_temp(repo_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Repo clone failed: {e}")

        for py in get_python_files(repo_path):
            tasks.append(analyze_async(py))

    if not tasks:
        raise HTTPException(status_code=400, detail="No valid input")

    results = await asyncio.gather(*tasks)

    overall_pre = sum(r["pre_confidence"] for r in results) / len(results)

    # Redis cache (safe)
    r = safe_redis()
    if r:
        try:
            r.set("latest_session", json.dumps({"files": len(results)}))
        except:
            pass

    # PostgreSQL (safe)
    conn = safe_pg()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            conn.commit()
            cur.close()
            conn.close()
        except:
            pass

    return {
        "overall_pre_confidence": round(overall_pre, 2),
        "files": results,
    }
