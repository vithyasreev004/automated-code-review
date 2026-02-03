from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from pathlib import Path
import asyncio

from .utils import save_uploaded_file_temp, extract_zip_temp, clone_github_repo_temp, get_python_files
from app.static_analysis.structure_extractor import parse_file, extract_structure
from app.static_analysis.static_analysis import analyze_file
from app.llm.review_llm import run_llm_review

app = FastAPI(title="Automated Code Review")


def analyze_sync(file_path: Path):
    tree = parse_file(file_path)
    structure = extract_structure(tree)
    analysis = analyze_file(file_path)

    llm_review = run_llm_review(structure, analysis)

    return {
        "file": str(file_path),
        "structure": structure,
        "analysis": analysis,
        "llm_review": llm_review,
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

    # -------- Aggregate confidence --------
    confidences = []
    for r in results:
        try:
            confidences.append(int(eval(r["llm_review"])["confidence"]))
        except Exception:
            pass

    overall_confidence = (
        sum(confidences) / len(confidences) if confidences else 0
    )

    return {
        "overall_confidence": round(overall_confidence, 2),
        "files": results,
    }
