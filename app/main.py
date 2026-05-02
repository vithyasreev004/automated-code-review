from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from typing import List, Optional
from pathlib import Path
import asyncio
import json
import logging
import os

from app.core.security import verify_api_key

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

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

from psycopg2.extras import Json
from pydantic import ValidationError

from app.models import LLMReview, RefactorResult, DocResult

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------------------
# App Init
# -------------------------------
app = FastAPI(title="Automated Code Review")

@app.get("/")
def root():
    return {"message": "API is running 🚀"}

# -------------------------------
# Rate Limiter
# -------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Rate limit exceeded", "status": 429})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": str(exc), "status": 500})

# -------------------------------
# SAFE LLM WRAPPERS (with timeout + key check)
# -------------------------------
LLM_TIMEOUT = 10

async def safe_llm_review(structure, analysis):
    if not os.getenv("GROQ_API_KEY"):
        return {"summary": "LLM skipped (no API key)", "issues": []}
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(run_llm_review, structure, analysis),
            timeout=LLM_TIMEOUT
        )
        return LLMReview.parse_obj(raw).dict()
    except Exception as e:
        return {"summary": f"LLM error: {e}", "issues": []}

async def safe_refactor(original_code, analysis):
    if not os.getenv("GROQ_API_KEY"):
        return {"refactored_code": original_code, "diff": "LLM skipped"}
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(run_llm_refactor, original_code, analysis),
            timeout=LLM_TIMEOUT
        )
        return RefactorResult.parse_obj(raw).dict()
    except Exception as e:
        return {"refactored_code": original_code, "diff": f"Error: {e}"}

async def safe_docstrings(code):
    if not os.getenv("GROQ_API_KEY"):
        return {"documented_code": code}
    try:
        raw = await asyncio.wait_for(
            asyncio.to_thread(run_llm_docstrings, code),
            timeout=LLM_TIMEOUT
        )
        return DocResult.parse_obj(raw).dict()
    except Exception as e:
        return {"documented_code": code}

# -------------------------------
# ANALYSIS
# -------------------------------
async def analyze_file_async(file_path: Path):
    tree = parse_file(file_path)
    structure = extract_structure(tree)
    analysis = analyze_file(file_path)

    llm_review = await safe_llm_review(structure, analysis)
    pre_conf = calculate_confidence(analysis)

    original_code = file_path.read_text(encoding="utf-8")

    refactor = await safe_refactor(original_code, analysis)
    doc = await safe_docstrings(refactor["refactored_code"])

    return {
        "file": str(file_path),
        "analysis": analysis,
        "llm_review": llm_review,
        "pre_confidence": pre_conf,
        "refactored_code": refactor["refactored_code"],
        "diff": refactor["diff"],
        "documented_code": doc["documented_code"],
        "post_confidence": pre_conf,  # keep simple
        "issues": analysis.get("issues", [])
    }

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
    logger.info("Upload triggered")

    MAX_FILE_SIZE = 2 * 1024 * 1024
    MAX_FILES = 5   # 🔥 IMPORTANT LIMIT

    tasks = []

    # -------------------------------
    # FILE UPLOAD
    # -------------------------------
    if files:
        files = [f for f in files if f.filename]  # ignore empty

        for file in files:
            content = await file.read()

            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")

            file.file.seek(0)

            file_path, _ = save_uploaded_file_temp(file)

            tasks.append(analyze_file_async(file_path))

    # -------------------------------
    # GITHUB REPO
    # -------------------------------
    if repo_url:
        repo_path, _ = clone_github_repo_temp(repo_url)

        py_files = get_python_files(repo_path)

        if not py_files:
            raise HTTPException(status_code=400, detail="No Python files found")

        py_files = py_files[:MAX_FILES]  # 🔥 LIMIT

        for py in py_files:
            tasks.append(analyze_file_async(py))

    if not tasks:
        raise HTTPException(status_code=400, detail="No input provided")

    results = await asyncio.gather(*tasks)

    overall_pre = sum(r["pre_confidence"] for r in results) / len(results)

    # README
    readme = None
    if repo_url:
        try:
            readme = run_llm_readme(results, overall_pre, overall_pre)
        except Exception as e:
            readme = f"README failed: {e}"

    # Redis (safe)
    try:
        r = get_redis_connection()
        r.set("latest_session", json.dumps({
            "repo": repo_url or "files",
            "files": len(results),
            "pre_conf": round(overall_pre, 2)
        }))
    except:
        pass

    # PostgreSQL (safe)
    try:
        conn = get_pg_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO public.analysis_runs
            (repo, files, overall_pre_confidence, overall_post_confidence, results)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (repo_url or "files", len(results), overall_pre, overall_pre, Json(results))
        )

        conn.commit()
        cur.close()
        conn.close()
    except:
        pass

    return {
        "overall_pre_confidence": round(overall_pre, 2),
        "files": results,
        "readme": readme,
    }
