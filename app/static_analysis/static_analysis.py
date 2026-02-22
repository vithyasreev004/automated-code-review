import subprocess
import json
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from bandit.core import manager as bandit_manager
from bandit.core import config as bandit_config

def run_radon(file_path):
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
    try:
        result = subprocess.run(["pylint", file_path, "-rn", "-f", "json"],
                                capture_output=True, text=True)
        if result.stdout:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []

def analyze_file(file_path):
    return {
        "radon": run_radon(file_path),
        "bandit": run_bandit(file_path),
        "pylint": run_pylint(file_path)
    }

def calculate_confidence(analysis: dict) -> int:
    score = 100
    score -= len(analysis.get("pylint", [])) * 2
    score -= len(analysis.get("bandit", [])) * 5
    for c in analysis.get("radon", {}).get("cyclomatic_complexity", []):
        if c["complexity"] > 10:
            score -= 5
    return max(score, 0)
