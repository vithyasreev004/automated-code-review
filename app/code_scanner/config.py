"""_summary_
    Alright, I’m going to be **very direct and intellectually honest**, because what you wrote is **ambitious and good**, but also **over-scoped for one person if approached naïvely**. The right move is not “learn everything at once”, but to **sequence concepts so each one unlocks a concrete project milestone**.

Below is a **from-scratch learning + building roadmap**, where **every concept is tied to a tangible feature** of *your exact project*. No fluff, no hype.

# First: Reality Check (important)
Your project is **NOT** “an LLM project”.
It is primarily a **software engineering + systems integration project**.
LLMs are only **one component**.
If you try to “learn all GenAI concepts first”, you’ll stall.
If you build **incrementally**, this becomes very doable.
So we’ll proceed in **layers**.
---
# PHASE 0 — Prerequisites (Don’t skip)
You already know Python, Django/FastAPI basics. What you *must* be solid at:
### Concepts
* Python functions, classes, modules
* File I/O
* Exceptions
* Virtual environments
* Basic async (`async`, `await`)
* JSON handling

### Why

Everything else builds on this.

### Mini test

Write a Python script that:

* Reads all `.py` files from a folder
* Prints number of functions per file
* Handles syntax errors gracefully

If you can’t do this comfortably → stop and fix this first.

---

# PHASE 1 — Code Ingestion & Parsing (FOUNDATION)

This phase has **zero AI**.
It’s about understanding code **as data**.

---

## 1. File Upload & Repository Ingestion

### Concepts to Learn

* File upload handling (FastAPI / Streamlit)
* ZIP extraction
* Git cloning (`GitPython`)
* Directory traversal (`os.walk`, `pathlib`)

### What You Build

✅ Upload:

* Single file
* Multiple files
* ZIP archive
* GitHub repo URL

### Example

```python
from pathlib import Path

def collect_code_files(root: str):
    exts = {".py", ".js", ".java", ".cpp", ".h"}
    return [
        p for p in Path(root).rglob("*")
        if p.suffix in exts
    ]
```

### Tests

* Upload invalid ZIP → graceful error
* Repo >100MB → reject
* File >50KB → reject

---

## 2. Language Detection

### Concepts

* File extensions
* Heuristic syntax checks
* Tree-sitter basics (later)

### What You Build

```python
def detect_language(file_path):
    if file_path.endswith(".py"):
        return "python"
    if file_path.endswith(".js"):
        return "javascript"
```

⚠️ Don’t over-engineer this early.

---

## 3. Syntax Validation & AST Parsing (CRITICAL)

### Concepts

* AST (Abstract Syntax Tree)
* Why AST > regex
* Python `ast` module

### What You Build

```python
import ast

def parse_python(code: str):
    try:
        return ast.parse(code)
    except SyntaxError as e:
        return {"error": str(e)}
```

### What This Enables

* Count functions
* Extract classes
* Extract docstrings
* Detect complexity later

### Tests

* Valid Python → parsed
* Syntax error → clean error message

---

# PHASE 2 — Static Code Analysis (NO AI YET)

This is where your project becomes **serious**.

---

## 4. Linting & Style Checks

### Concepts

* What linters do vs formatters
* Exit codes
* Parsing CLI output

### Tools

* `pylint`
* `flake8`
* `black` (formatter)

### What You Build

Run linters **programmatically**:

```python
import subprocess

def run_pylint(file):
    result = subprocess.run(
        ["pylint", file, "--output-format=json"],
        capture_output=True,
        text=True
    )
    return result.stdout
```

### Output Example

```json
{
  "type": "warning",
  "message": "Unused variable",
  "line": 23
}
```

---

## 5. Complexity Analysis

### Concepts

* Cyclomatic complexity
* Why complexity matters
* Thresholds

### Tool

* `radon`

```python
from radon.complexity import cc_visit

def complexity(code):
    return cc_visit(code)
```

### What You Produce

* Complexity per function
* Flag functions > threshold

---

## 6. Security Scanning (STATIC)

### Concepts

* SAST vs DAST
* False positives

### Tools

* `bandit` (Python)
* `npm audit` (JS)

### Output

```json
{
  "severity": "HIGH",
  "issue": "Hardcoded password",
  "line": 12
}
```

---

### At this point:

🔥 You already have an **Automated Code Review Tool WITHOUT AI**

This alone is internship-worthy.

---

# PHASE 3 — LLM Fundamentals (ESSENTIAL, NOT MAGIC)

Now we bring AI **responsibly**.

---

## 7. What an LLM Actually Is (no hype)

### Concepts

* Tokens
* Context window
* Determinism vs temperature
* Prompt ≠ magic

### Hard Truth

LLMs:

* Do not understand code
* Predict text
* Can hallucinate confidently

Your job: **constrain them**

---

## 8. Prompt Engineering for Code Review

### Concepts

* System vs user prompts
* Structured output
* Few-shot prompting
* JSON schema enforcement

### Example Prompt

```text
You are a senior code reviewer.
Rules:
- No generic advice
- Cite line numbers
- Output JSON only
```

### Example Output Schema

```json
{
  "issues": [
    {
      "severity": "High",
      "category": "Security",
      "line": 42,
      "suggestion": "Use parameterized queries"
    }
  ]
}
```

---

## 9. LLM Integration (HuggingFace / OpenAI)

### Concepts

* API calls
* Rate limiting
* Retries
* Token usage tracking

### Example

```python
from huggingface_hub import InferenceClient

client = InferenceClient(model="bigcode/starcoder")

resp = client.text_generation(prompt)
```

### Validation

* Reject non-JSON output
* Retry with stricter prompt

---

# PHASE 4 — LLM-Based Code Review (CORE FEATURE)

Now combine **static analysis + LLM**.

---

## 10. Hybrid Review Strategy (IMPORTANT)

### Correct Architecture

❌ LLM-only review
✅ Static tools → LLM explanation

### Pipeline

1. Linter finds issue
2. LLM explains issue
3. LLM suggests fix

This **reduces hallucination massively**.

---

## 11. Structured Review Categories

You already listed them. Implement as enums:

```python
class Severity(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
```

---

# PHASE 5 — Documentation Generation (CONTROLLED AI)

---

## 12. Docstring Generation

### Concepts

* Google vs NumPy style
* Extract function signature from AST

```python
def extract_functions(tree):
    return [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
```

### Prompt Input

* Function name
* Params
* Existing docstring
* Function body

---

## 13. README Generation

### Reality Check

LLMs are good at README **templates**, not facts.

### Correct Approach

* You provide:

  * Project name
  * Dependencies
  * Entry points
* LLM fills language

---

## 14. API Documentation

### Concepts

* OpenAPI
* Swagger
* Why auto-generation matters

Use:

* FastAPI auto docs
* LLM only for descriptions

---

# PHASE 6 — Scoring, Prioritization & Metrics

---

## 15. Code Quality Scoring

### Simple Formula

```text
Score = 100
- (Critical * 20)
- (High * 10)
- (Medium * 5)
```

⚠️ Scoring is subjective. Document assumptions.

---

## 16. Monitoring Dashboard

### Concepts

* Aggregations
* Time-series
* Metrics ≠ insights

### Tools

* Pandas
* Streamlit charts

---

# PHASE 7 — UI & Interaction

---

## 17. Diff Visualization

### Concepts

* Unified diff
* Before/after

```python
import difflib
```

---

## 18. One-click Fixes (Advanced)

### Reality Check

Auto-applying fixes is **dangerous**.

Start with:

* Diff preview
* Manual apply

---

# PHASE 8 — Testing & Reliability (MOST PEOPLE SKIP THIS)

---

## 19. Testing Strategy

### Concepts

* Unit tests for parsers
* Snapshot tests for LLM output
* Mock LLM calls

Use:

* `pytest`
* JSON schema validation

---

## 20. Security & Sandbox

### Concepts

* Never execute user code
* Scan secrets before LLM
* Rate limiting

---

# Final Honest Assessment

If done properly, this project shows:

* Strong backend engineering
* Practical GenAI usage
* System design maturity
* Production thinking

🚫 It is **not** a “toy AI project”.
✅ It is **job-relevant** for GenAI / Backend roles.

---

## Next Step (Important)

If you want, next we can:

1. **Break this into a 6-week execution plan**, OR
2. Start **Phase 1 hands-on** (actual FastAPI project structure), OR
3. Convert this into a **resume-ready project description**, OR
4. I act as a **strict reviewer** and challenge your design choices

Tell me **which one**, and I’ll go deep.

"""
SUPPORTED_EXTENSIONS = {'.py', '.js', '.java', '.cpp'}
MAX_FILE_SIZE = 50 * 1024
