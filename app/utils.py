import tempfile
from pathlib import Path
import zipfile
import os
import shutil
from git import Repo, GitCommandError

# -------------------------------
# Redis configuration
# -------------------------------
import redis

def get_redis_connection():
    return redis.Redis(host="localhost", port=6379, db=0)

# -------------------------------
# PostgreSQL connection
# -------------------------------
import psycopg2
from psycopg2.extras import Json

def get_pg_connection():
    return psycopg2.connect(
        dbname="reviewdb",
        user="postgres",
        password="admin123",
        host="localhost",
        port="5432"
    )

# -------------------------------
# File Handling
# -------------------------------
MAX_FILE_SIZE = 50 * 1024  # 50 KB per file (adjust if needed)

def save_uploaded_file_temp(file):
    """Save an uploaded file to a temporary directory and return path + temp_dir object."""
    temp_dir = tempfile.TemporaryDirectory()
    file_path = Path(temp_dir.name) / file.name
    with open(file_path, "wb") as f:
        f.write(file.read())
    return file_path, temp_dir

def extract_zip_temp(file_path: Path):
    """Extract a zip file into a temporary directory."""
    temp_dir = tempfile.TemporaryDirectory()
    extract_path = Path(temp_dir.name)
    with zipfile.ZipFile(file_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)
    return extract_path, temp_dir

def clone_github_repo_temp(url: str):
    """Clone a GitHub repo into a temporary directory."""
    temp_dir = tempfile.TemporaryDirectory()
    repo_path = Path(temp_dir.name)
    try:
        Repo.clone_from(url, repo_path)
    except GitCommandError as e:
        raise RuntimeError(f"Failed to clone repo: {url}\nError: {str(e)}")
    return repo_path, temp_dir

def get_python_files(root_path: Path):
    """Recursively collect all Python files under root_path, respecting MAX_FILE_SIZE."""
    py_files = []
    for root, dirs, files in os.walk(root_path):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() == ".py" and file_path.stat().st_size <= MAX_FILE_SIZE:
                py_files.append(file_path)
    return py_files

def chunk_code(content: str, max_chunk_size: int = 2000):
    """Split code into chunks of ~max_chunk_size characters."""
    return [content[i:i+max_chunk_size] for i in range(0, len(content), max_chunk_size)]

# -------------------------------
# Cleanup
# -------------------------------
def cleanup_temp_dirs(temp_dirs):
    """Remove temporary directories after use."""
    for d in temp_dirs:
        if hasattr(d, "cleanup"):
            d.cleanup()
        else:
            shutil.rmtree(str(d), ignore_errors=True)
