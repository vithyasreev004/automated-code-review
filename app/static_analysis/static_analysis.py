import subprocess
import json
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from bandit.core import manager as bandit_manager
from bandit.core import config as bandit_config

def run_radon(file_path):
    """Cyclomatic complexity & maintainability index"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        complexity = cc_visit(code)
        mi = mi_visit(code, True)
        cc_list = [{"name": c.name, "line": c.lineno, "complexity": c.complexity} for c in complexity]
        return {"cyclomatic_complexity": cc_list, "maintainability_index": mi}
    except Exception:
        return {}

def run_bandit(file_path):
    """Run bandit analysis programmatically"""
    try:
        b_conf = bandit_config.BanditConfig()
        mgr = bandit_manager.BanditManager(b_conf, "file")
        mgr.discover_files([str(file_path)])
        mgr.run_tests()
        results = []
        for issue in mgr.results:
            results.append({
                "filename": issue.fname,
                "line": issue.lineno,
                "severity": issue.severity,
                "confidence": issue.confidence,
                "issue_text": issue.text,
                "category": issue.test_id
            })
        return results
    except Exception:
        return []

def run_pylint(file_path):
    """Run pylint and return issues"""
    try:
        result = subprocess.run(["pylint", file_path, "-rn", "-f", "json"],
                                capture_output=True, text=True)
        if result.stdout:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []

def analyze_file(file_path):
    """Run all static analysis and return dict"""
    return {
        "radon": run_radon(file_path),
        "bandit": run_bandit(file_path),
        "pylint": run_pylint(file_path)
    }
