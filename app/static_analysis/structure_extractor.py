import ast

def parse_file(file_path):
    """Return AST tree"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return ast.parse(content)

def extract_structure(tree):
    """Return classes and functions info"""
    classes = []
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append({"name": node.name, "line": node.lineno})
        elif isinstance(node, ast.FunctionDef):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args]
            })
    return {"classes": classes, "functions": functions}
