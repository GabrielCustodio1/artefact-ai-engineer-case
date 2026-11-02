# 🎸 Empório da Música - AI Customer Assistant

An intelligent, 100% local conversational agent built to handle customer support for **Empório da Música** (founded in 2008 in Campo Grande/MS, Brazil). The application operates completely offline with zero external cloud API dependencies, connecting an open-weights LLM running via Ollama to a local relational SQLite database and a PDF policy manual.

---

## 🛠️ Architecture & Technical Decisions

* **Core Language:** Python 3.10+
* **User Interface:** Streamlit chat interface
* **Inference Engine:** 100% Local execution via **Ollama** using `qwen2.5:7b-instruct-q4_K_M`.
* **Privacy & Security:** Complete data privacy with zero external telemetry or third-party cloud API dependencies.
* **Tool Calling Orchestration:** The assistant runs an iterative loop that inspects model tool calls, executes the corresponding Python functions sequentially, feeds back tool results, and returns the final synthesized response.
* **Database & Search:** Local SQLite database with custom Unicode normalization functions (`unaccent`) for accent-insensitive search, budget filtering, and price ordering.
* **Document Retrieval:** Multi-page lexical extraction and relevance scoring using `pypdf`, providing full page contexts without arbitrary character truncation to preserve physical addresses, business hours, and shipping fees.

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone [https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git](https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git)
cd artefact-ai-engineer-case
2. Set Up Virtual Environment
Bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Initialize Database
Bash
python init_db.py
5. Start the Local Ollama Model
Ensure Ollama is installed and running locally, then pull and run the model:

Bash
ollama run qwen2.5:7b-instruct-q4_K_M
6. Run the Application
Bash
streamlit run app.py
🔍 Available Tools
buscar_produtos: Searches instruments in the database with accent stripping, price ordering (ASC/DESC), budget cap constraints, and diagnostics for items exceeding budgets or out of stock.

consultar_pedido: Retrieves detailed order status, carrier tracking codes, delivery estimates, and item lists by order_id.

consultar_politicas: Extracts store operational rules, return windows (7-day regret), 90-day warranty, local shipping fees (R$ 35.00 for Campo Grande), business hours, and physical address from the official PDF manual.

⚠️ Known Limitations
Sequential Tool Execution: Multi-tool requests are processed sequentially within an iterative loop rather than asynchronously in parallel (asyncio.gather).

Historical Order Pricing: The relational schema in order_items lacks a snapshot unit price at purchase time; the current price from products is displayed instead.

No Customer Order Authentication: As a demonstration prototype, order lookup only requires order_id without verifying customer ownership (e.g., CPF or email validation).

Lexical Retrieval for PDF: Policy retrieval relies on keyword scoring and full-page text ranking rather than a dense vector database (e.g., ChromaDB/pgvector).

🔮 Future Improvements & Next Steps
RAG with Vector Embeddings: Replace lexical page matching with dense embeddings (e.g., bge-small-en-v1.5 or all-MiniLM-L6-v2 served locally) and a local vector store.

Parallel Tool Invocation: Implement asynchronous execution (asyncio) when the local model requests multiple tools in a single turn.

Customer Identity Verification: Add a two-step verification layer (order ID + email/CPF) before exposing customer order details.

Automated Testing Suite: Add end-to-end and unit tests using pytest along with a GitHub Actions CI workflow to validate tool outputs and prompt regressions.

Local Semantic Cache: Integrate a local SQLite-based cache to reduce local inference latency on repeated queries.

🤖 AI Assistants & Development Workflow
During the development and refactoring of this case:

Tools Used: Anthropic Claude 3.5 Sonnet and OpenAI GPT-4o.

Workflow: AI assistants were utilized to refactor SQLite query logic (such as custom unaccent registration), format OpenAI-standard function calling schemas, write structured Markdown documentation, and design synthetic edge-case tests. All business logic, schemas, and outputs were verified through local execution.
