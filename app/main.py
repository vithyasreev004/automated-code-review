from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from pathlib import Path
import asyncio

from app.utils import save_uploaded_file_temp, clone_github_repo_temp, get_python_files
from app.static_analysis.structure_extractor import parse_file, extract_structure
from app.static_analysis.static_analysis import analyze_file, calculate_confidence
from app.llm.review_llm import run_llm_review
from app.llm.refactor_llm import run_llm_refactor
from app.llm.doc_llm import run_llm_docstrings
from app.llm.readme_llm import run_llm_readme   # NEW

app = FastAPI(title="Automated Code Review")

def analyze_sync(file_path: Path):
    tree = parse_file(file_path)
    structure = extract_structure(tree)
    analysis = analyze_file(file_path)

    llm_review = run_llm_review(structure, analysis)
    pre_confidence = calculate_confidence(analysis)

    original_code = file_path.read_text(encoding="utf-8")
    refactor_result = run_llm_refactor(original_code, analysis)
    refactored_code = refactor_result.get("refactored_code", "")
    diff = refactor_result.get("diff", "")

    doc_result = run_llm_docstrings(refactored_code)
    documented_code = doc_result.get("documented_code", "")

    temp_file = file_path.parent / f"{file_path.stem}_refactored.py"
    temp_file.write_text(refactored_code, encoding="utf-8")
    post_analysis = analyze_file(temp_file)
    post_confidence = calculate_confidence(post_analysis)

    return {
        "file": str(file_path),
        "structure": structure,
        "analysis": analysis,
        "llm_review": llm_review,
        "pre_confidence": pre_confidence,
        "refactored_code": refactored_code,
        "diff": diff,
        "documented_code": documented_code,
        "post_confidence": post_confidence,
    }

async def analyze_async(file_path: Path):
    return await asyncio.to_thread(analyze_sync, file_path)

@app.post("/upload-code/")
async def upload_code(
    files: List[UploadFile] = File(None),
    repo_url: Optional[str] = Form(None),
):
    tasks = []
    temp_dirs = []

    if files:
        for file in files:
            file_path, temp_dir = save_uploaded_file_temp(file)
            temp_dirs.append(temp_dir)
            for py in get_python_files(file_path.parent):
                tasks.append(analyze_async(py))

    if repo_url:
        repo_path, temp_dir = clone_github_repo_temp(repo_url)
        temp_dirs.append(temp_dir)
        for py in get_python_files(repo_path):
            tasks.append(analyze_async(py))

    results = await asyncio.gather(*tasks)

    overall_pre = sum(r["pre_confidence"] for r in results) / len(results) if results else 0
    overall_post = sum(r["post_confidence"] for r in results) / len(results) if results else 0

    # NEW: generate README for repo if repo_url provided
    readme = None
    if repo_url:
        readme = run_llm_readme(results, overall_pre, overall_post)

    return {
        "overall_pre_confidence": round(overall_pre, 2),
        "overall_post_confidence": round(overall_post, 2),
        "files": results,
        "readme": readme,
    }
