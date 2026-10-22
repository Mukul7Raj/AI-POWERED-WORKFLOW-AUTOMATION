# AI-Powered Workflow Automation Agent (Agentic AI)

A lightweight autonomous agent that extracts structured data from unstructured documents, validates schemas, stores records in a database (SQLite / PostgreSQL), and routes ambiguous cases to a human review queue.

---

## ⚡ Key Highlights
* **Autonomous Ingestion:** Parses raw receipts, invoices, and documents into structured schemas.
* **Schema Validation & Retry Logic:** Pydantic validation + exponential backoff retry to guard against LLM API failures and hallucinations.
* **Human-in-the-Loop Routing:** Automatically routes low-confidence extractions (`confidence < 0.80`) to a review queue instead of corrupting the database.
* **Zero-Setup Demo:** Works instantly with local SQLite and a built-in fallback parser if no OpenAI API key is provided.

---

## 🚀 Quick Start (Under 1 Minute)

### 1. Run the CLI Demo
```bash
python main.py
```
This processes sample documents in `sample_documents/` and prints the database status table.

### 2. Run the Visual Dashboard (Streamlit)
```bash
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) to view:
- **Ingestion Dashboard:** Live list of all processed records.
- **Human Review Queue:** Approve or reject flagged documents with 1 click.
- **Ingest New Document:** Paste any raw invoice/receipt text to test in real time.

---

## ⚙️ Configuration (Optional)
To use OpenAI or PostgreSQL, copy `.env.example` to `.env`:
```ini
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite:///workflow_agent.db  # Or postgresql://user:pass@localhost:5432/dbname
```

---

## 📁 Project Structure
```
AI WORKFLOW AUTOMATION/
├── agent.py               # Core LLM agent with retry logic & confidence routing
├── models.py              # Pydantic schemas & SQLAlchemy DB models
├── database.py            # SQLite & PostgreSQL persistence layer
├── main.py                # Command-line demo runner
├── app.py                 # Streamlit web UI & human review dashboard
├── sample_documents/      # Clean & messy text samples for testing
├── .env.example           # Config template for OpenAI & PostgreSQL
└── README.md              # Documentation
```
