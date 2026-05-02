from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Request
from typing import List, Optional
from pathlib import Path
import asyncio
import json
import logging

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

# -------------------------------
# Rate Limiter
# -------------------------------
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "status": 429},
    )

# -------------------------------
# Global Error Handler
# -------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "status": 500}
    )

# -------------------------------
# LLM Timeout Wrapper
# -------------------------------
async def run_with_timeout(func, *args, timeout=20):
    return await asyncio.wait_for(asyncio.to_thread(func, *args), timeout=timeout)

# -------------------------------
# Safe Wrappers
# -------------------------------
async def safe_llm_review(structure, analysis):
    try:
        raw = await run_with_timeout(run_llm_review, structure, analysis)
        return LLMReview.parse_obj(raw).dict()
    except Exception as e:
        return LLMReview(summary=f"LLM error: {e}").dict()

async def safe_refactor(original_code, analysis):
    try:
        raw = await run_with_timeout(run_llm_refactor, original_code, analysis)
        return RefactorResult.parse_obj(raw).dict()
    except Exception as e:
        return RefactorResult(
            refactored_code=original_code,
            diff=f"Refactor failed: {e}"
        ).dict()

async def safe_docstrings(refactored_code):
    try:
        raw = await run_with_timeout(run_llm_docstrings, refactored_code)
        return DocResult.parse_obj(raw).dict()
    except Exception as e:
        return DocResult(
            documented_code=f'"""Stub (error: {e})"""\n{refactored_code}'
        ).dict()

# -------------------------------
# Analysis Logic
# -------------------------------
async def analyze_async(file_path: Path):
    tree = parse_file(file_path)
    structure = extract_structure(tree)
    analysis = analyze_file(file_path)

    llm_review = await safe_llm_review(structure, analysis)
    pre_confidence = calculate_confidence(analysis)

    original_code = file_path.read_text(encoding="utf-8")

    refactor_result = await safe_refactor(original_code, analysis)
    documented_result = await safe_docstrings(refactor_result["refactored_code"])

    temp_file = file_path.parent / f"{file_path.stem}_refactored.py"
    temp_file.write_text(refactor_result["refactored_code"], encoding="utf-8")

    post_analysis = analyze_file(temp_file)
    post_confidence = calculate_confidence(post_analysis)

    all_issues = []

    for i in llm_review.get("issues", []):
        i["source"] = "LLM"
        all_issues.append(i)

    for i in analysis.get("issues", []):
        i["source"] = "Static"
        all_issues.append(i)

    for i in documented_result.get("issues", []):
        i["source"] = "Docstring"
        all_issues.append(i)

    return {
        "file": str(file_path),
        "structure": structure,
        "analysis": analysis,
        "llm_review": llm_review,
        "pre_confidence": pre_confidence,
        "refactored_code": refactor_result["refactored_code"],
        "diff": refactor_result["diff"],
        "documented_code": documented_result["documented_code"],
        "post_confidence": post_confidence,
        "issues": all_issues,
    }

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
    logger.info("Upload endpoint triggered")

    tasks = []
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

    # ---------------- FILE UPLOAD ----------------
    if files:
        for file in files:
            contents = await file.read()

            if len(contents) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")

            file.file.seek(0)
            file_path, _ = save_uploaded_file_temp(file)

            for py in get_python_files(file_path.parent):
                tasks.append(analyze_async(py))

    # ---------------- REPO ----------------
    if repo_url:
        logger.info(f"Cloning repo: {repo_url}")

        try:
            repo_path, _ = clone_github_repo_temp(repo_url)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Git clone failed: {e}")

        py_files = list(get_python_files(repo_path))

        if not py_files:
            raise HTTPException(status_code=400, detail="No Python files found")

        for py in py_files:
            tasks.append(analyze_async(py))

    if not tasks:
        raise HTTPException(status_code=400, detail="No input provided")

    results = await asyncio.gather(*tasks)

    overall_pre = sum(r["pre_confidence"] for r in results) / len(results)
    overall_post = sum(r["post_confidence"] for r in results) / len(results)

    summary = {
        "repo": repo_url if repo_url else "uploaded_files",
        "files": len(results),
        "pre_conf": round(overall_pre, 2),
        "post_conf": round(overall_post, 2),
    }

    # ---------------- REDIS (OPTIONAL) ----------------
    try:
        r = get_redis_connection()
        if r:
            r.set("latest_session", json.dumps(summary))
    except Exception as e:
        logger.warning(f"Redis not available: {e}")

    # ---------------- POSTGRES (OPTIONAL) ----------------
    try:
        conn = get_pg_connection()
        if conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO public.analysis_runs
                (repo, files, overall_pre_confidence, overall_post_confidence, results)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    summary["repo"],
                    summary["files"],
                    summary["pre_conf"],
                    summary["post_conf"],
                    Json(results)
                )
            )
            conn.commit()
            cur.close()
            conn.close()
    except Exception as e:
        logger.warning(f"PostgreSQL not available: {e}")

    return {
        "overall_pre_confidence": summary["pre_conf"],
        "overall_post_confidence": summary["post_conf"],
        "files": results,
    }
