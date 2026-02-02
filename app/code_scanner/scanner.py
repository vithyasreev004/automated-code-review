import os
from pathlib import Path

CODE_EXTS = [".py", ".js", ".cpp", ".java"]

def scan_repository(repo_path: Path):
    """
    Recursively scan a folder (repo or extracted ZIP) and return Python file paths
    """
    python_files = []
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in CODE_EXTS:
                python_files.append(file_path)
    return python_files
