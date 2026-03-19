# Automated Code Review & Documentation Assistant
## Overview
The **Automated Code Review & Documentation Assistant** is a Python‑focused tool that reviews code and generates documentation.  
It combines static analysis with LLM‑powered insights to highlight issues, suggest improvements, and produce refactored/documented code.  
The system integrates with **PostgreSQL** for persistence, **Redis** for caching, and **Streamlit** for an interactive dashboard.
## Features Implemented
- 📂 Upload Python files or connect GitHub repositories for analysis  
- 🔍 Chunking of large files for scalable review  
- 📝 LLM review summaries, issue detection, diffs, refactored/documented code outputs  
- 📊 Confidence metrics (pre/post analysis) displayed in the dashboard  
- 💾 Persistence in PostgreSQL (sessions, runs, file results, error logs)  
- ⚡ Redis caching for latest session data  
- 🗂 History panel with run management (view, delete, clear, new chat)  
- 🚨 Error logging with proper database integration and sidebar display  
- 📑 Export options: JSON, Markdown, PDF reports  
- 📈 Monitoring dashboard with KPIs and interactive charts  
## Tech Stack
- **Python** – core language  
- **Streamlit** – interactive dashboard UI  
- **PostgreSQL** – database for sessions, runs, file results, error logs  
- **Redis** – caching layer for latest session data  
- **SQLAlchemy** – ORM for database interactions  
- **FPDF** – PDF report generation  
- **LLM Integration** – for review summaries, diffs, refactored/documented code  
## Current Status
- ✅ Core functionality complete  
- ✅ Error logging fixed and integrated with PostgreSQL  
- ✅ Dashboard panels refined (Per‑File Results & Error Logs in sidebar)  
- ✅ Export options implemented (JSON, Markdown, PDF)  
- ⏳ CI/CD pipeline setup next  
- ⏳ Multi‑language support optional, not required for current scope  

## Getting Started

### Prerequisites
- Python 3.9+  
- PostgreSQL (running locally or remotely)  
- Redis (running locally or remotely)  

### Installation
Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/automated-code-review-assistant.git
cd automated-code-review-assistant
pip install -r requirements.txt
```

### Database Setup
Create the required PostgreSQL database and tables:

```sql
CREATE DATABASE reviewdb;
```

Run the schema scripts (if provided) or ensure tables exist:  
- `sessions`  
- `analysis_runs`  
- `file_results`  
- `errors`

### Running the App
Start the Streamlit dashboard:

```bash
streamlit run app.py
```

### Usage
- Upload a Python file or provide a GitHub repository URL.  
- View analysis results, confidence metrics, and LLM‑powered suggestions.  
- Check error logs and per‑file results in the sidebar.  
- Export reports in JSON, Markdown, or PDF formats.  



Would you like me to also add a **“Screenshots” section** with placeholders, so you can drop in images of your dashboard panels (Latest Session, Error Logs, Per‑File Results) to make the README visually appealing?
