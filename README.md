# Automated Code Review & Documentation Assistant

## Overview
This project provides an automated assistant for reviewing Python code and generating documentation.  
It uses static analysis and LLM-powered insights to highlight issues, suggest improvements, and produce refactored/documented code.  
The system integrates with PostgreSQL for persistence, Redis for caching, and Streamlit for an interactive dashboard.

## Phase
**Phase 0 – Scope, contracts, and system foundations**

## Guarantees
- Python-only analysis  
- Static-analysis-first approach  
- No code execution inside the assistant  
- No model training required  

## Non-goals
- Auto-fixing code (beyond suggested diffs/refactors)  
- Multi-language support (optional, not in scope for Phase 0)  
- Full security audit  

## Features
- 📂 Upload Python files or connect GitHub repositories  
- 🔍 Chunking large files for scalable analysis  
- 📝 LLM review summaries, issues, diffs, refactored/documented code  
- 📊 Confidence metrics (pre/post analysis)  
- 💾 Persistence in PostgreSQL and caching in Redis  
- 🗂 History panel with run management (view, delete, clear, new chat)  
- 📑 Export options: JSON, Markdown, PDF  
- 📈 Monitoring dashboard with KPIs and interactive charts (Altair line, bar, pie)  

## Status
- ✅ Core functionality complete  
- ✅ Monitoring dashboard implemented  
- ✅ CI/CD pipeline setup next  
- ⏳ Multi-language support optional, not required for Phase 0  

