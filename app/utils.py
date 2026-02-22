import tempfile
from pathlib import Path
import zipfile
from git import Repo
import os

MAX_FILE_SIZE = 50 * 1024  # 50 KB per file

def save_uploaded_file_temp(file):
    temp_dir = tempfile.TemporaryDirectory()
    file_path = Path(temp_dir.name) / file.filename
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    return file_path, temp_dir

def extract_zip_temp(file_path: Path):
    temp_dir = tempfile.TemporaryDirectory()
    extract_path = Path(temp_dir.name)
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    return extract_path, temp_dir

def clone_github_repo_temp(url: str):
    temp_dir = tempfile.TemporaryDirectory()
    repo_path = Path(temp_dir.name)
    Repo.clone_from(url, repo_path)
    return repo_path, temp_dir

def get_python_files(root_path: Path):
    py_files = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() == ".py" and file_path.stat().st_size <= MAX_FILE_SIZE:
                py_files.append(file_path)
    return py_files
