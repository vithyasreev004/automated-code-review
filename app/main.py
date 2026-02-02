from fastapi import FastAPI, UploadFile, File, Form
from typing import List, Optional
from pathlib import Path

from .utils import save_uploaded_file_temp, extract_zip_temp, clone_github_repo_temp, get_python_files
from app.static_analysis.structure_extractor import parse_file, extract_structure
from app.static_analysis.static_analysis import analyze_file

import tempfile
import zipfile
import os

app = FastAPI(title="Automated Code Review")

@app.post("/upload-code/")
async def upload_code(files: List[UploadFile] = File(None), repo_url: Optional[str] = Form(None)):
    all_results = []

    temp_dirs = []

    # Handle single/multiple uploaded files
    if files:
        for file in files:
            file_path, temp_dir = save_uploaded_file_temp(file)
            temp_dirs.append(temp_dir)
            py_files = get_python_files(file_path.parent)
            for f in py_files:
                tree = parse_file(f)
                structure = extract_structure(tree)
                analysis = analyze_file(f)
                all_results.append({
                    "file": str(f),
                    "structure": structure,
                    "analysis": analysis
                })

    # Handle zip files inside uploaded files
    if files:
        for file in files:
            if Path(file.filename).suffix.lower() == ".zip":
                file_path, temp_dir = save_uploaded_file_temp(file)
                temp_dirs.append(temp_dir)
                extract_path, zip_temp_dir = extract_zip_temp(file_path)
                temp_dirs.append(zip_temp_dir)
                py_files = get_python_files(extract_path)
                for f in py_files:
                    tree = parse_file(f)
                    structure = extract_structure(tree)
                    analysis = analyze_file(f)
                    all_results.append({
                        "file": str(f),
                        "structure": structure,
                        "analysis": analysis
                    })

    # Handle GitHub repo
    if repo_url:
        repo_path, temp_dir = clone_github_repo_temp(repo_url)
        temp_dirs.append(temp_dir)
        py_files = get_python_files(repo_path)
        for f in py_files:
            tree = parse_file(f)
            structure = extract_structure(tree)
            analysis = analyze_file(f)
            all_results.append({
                "file": str(f),
                "structure": structure,
                "analysis": analysis
            })

    return {"results": all_results}
