from pathlib import Path
from .issues import Issue


def check_syntax(path: Path) -> list[Issue]:
    issues: list[Issue] = []

    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
    except SyntaxError as e:
        issues.append(
            Issue(
                file=path,
                message=e.msg,
                line=e.lineno,
                severity="CRITICAL",
                category="SYNTAX",
            )
        )

    return issues
