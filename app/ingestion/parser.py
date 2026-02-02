import ast
from typing import Dict, List

def parse_python_code(code: str) -> Dict[str, List[Dict]]:
    """
    Returns AST summary:
    - functions: list of dicts with 'name' and 'has_docstring'
    - classes: list of dicts with 'name' and 'has_docstring'
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {"functions": [], "classes": []}

    functions, classes = [], []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({"name": node.name, "has_docstring": bool(ast.get_docstring(node))})
        elif isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "has_docstring": bool(ast.get_docstring(node))})

    return {"functions": functions, "classes": classes}
