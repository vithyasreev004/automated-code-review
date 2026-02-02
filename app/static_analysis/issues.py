from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Issue:
    file: Path
    message: str
    line: Optional[int]
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    category: str  # "SYNTAX", later: "STYLE", "SECURITY"
