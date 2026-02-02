from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
from pathlib import Path
from app.code_scanner.scanner import scan_repository
from app.static_analysis.ast_parser import parse_ast
from app.static_analysis.structure_extractor import extract_structure
from app.static_analysis.static_analysis import run_static_analysis
from .utils import save_uploaded_file_temp, extract_zip_temp, clone_github_repo_temp

router = APIRouter()

@router.post("/upload-code/")
async def upload_code(
    files: Optional[List[UploadFile]] = File(None),
    repo_url: Optional[str] = Form(None)
):
    """
    Unified code input:
    - Multiple Python files
    - ZIP files
    - GitHub repository URL
    """
    results = []
    temp_dirs = []  # keep references alive

    # 1️⃣ Process uploaded files
    if files:
        for file in files:
            file_path, temp_dir = save_uploaded_file_temp(file)
            temp_dirs.append(temp_dir)

            if file_path.suffix.lower() == ".zip":
                extract_path, extract_temp_dir = extract_zip_temp(file_path)
                temp_dirs.append(extract_temp_dir)
                targets = scan_repository(extract_path)
            elif file_path.suffix.lower() == ".py":
                targets = [file_path]
            else:
                continue

            for path in targets:
                tree = parse_ast(path)
                if not tree:
                    continue
                structure = extract_structure(tree)
                analysis = run_static_analysis(path)
                results.append({
                    "file": str(path),
                    "structure": structure,
                    "analysis": analysis
                })

    # 2️⃣ Process GitHub repo
    if repo_url:
        repo_path, repo_temp_dir = clone_github_repo_temp(repo_url)
        temp_dirs.append(repo_temp_dir)

        paths = scan_repository(repo_path)
        for path in paths:
            tree = parse_ast(path)
            if not tree:
                continue
            structure = extract_structure(tree)
            analysis = run_static_analysis(path)
            results.append({
                "file": str(path),
                "structure": structure,
                "analysis": analysis
            })

    return {"results": results}
