import ast
from pathlib import Path
from typing import Optional


def parse_ast(path: Path) -> Optional[ast.AST]:
    """
    Returns AST if syntax is valid, otherwise None.
    """
    try:
        source = path.read_text(encoding="utf-8")
        return ast.parse(source)
    except SyntaxError:
        return None
