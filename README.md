# Empório da Música - AI Customer Support Agent
### Technical Case: AI Engineer – Full-Stack para Aplicações com IA Generativa | Artefact

An end-to-end AI-powered conversational agent designed for **Empório da Música**, a specialized musical instrument store founded in 2008 in Campo Grande/MS. The agent autonomously navigates structured inventory and order databases, extracts business rules from unstructured store policy documents, and interacts with customers through an intuitive web interface.

---

## 🚀 Live Demo & Links

- **Live Web Application:** [Streamlit Cloud App](https://artefact-ai-engineer-case.streamlit.app) *(substitute with your actual URL)*
- **GitHub Repository:** [github.com/GabrielCustodio1/artefact-ai-engineer-case](https://github.com/GabrielCustodio1/artefact-ai-engineer-case)

---

## 🏛️ System Architecture

The solution follows the **KISS principle (Keep It Simple, Stupid)**, favoring lightweight, maintainable, and deterministic implementations over unnecessary infrastructure complexity:

              ┌────────────────────────────────────────┐
              │       Streamlit Web Interface          │
              │               (app.py)                 │
              └──────────────────┬─────────────────────┘
                                 │ User Query
                                 ▼
              ┌────────────────────────────────────────┐
              │     Agentic Controller (agent.py)      │
              │  (ReAct Loop via OpenAI Compatible SDK)│
              └─────────┬────────────────────┬─────────┘
                        │                    │
          Tool Calling  ▼                    ▼ Tool Calling

┌────────────────────────────────┐   ┌────────────────────────────────┐
│     buscar_produtos(termo,     │   │   consultar_politicas(duvida)  │
│          preco_maximo)         │   │       (Unstructured RAG)       │
│   consultar_pedido(order_id)   │   └───────────────┬────────────────┘
│    (Structured SQL Engine)     │                   │
└───────────────┬────────────────┘                   ▼
│                           pypdf Text Matcher
▼                           (Zero vector-db overhead)
SQLite Database                              │
(emporio_musica.db)                             ▼
politicas_da_loja.pdf

### 1. Structured Data Engine (`tools.py`)
- **Database:** Local SQLite database (`emporio_musica.db`).
- **Catalog Search (`buscar_produtos`):** Case-insensitive wildcard queries with optional budget constraints, strictly querying instruments.
- **Order Retrieval (`consultar_pedido`):** Relational SQL joins between `orders`, `order_items`, and `products` ensuring accurate price, shipping, and delivery timelines.

### 2. Policy Manual Extraction (`consultar_politicas`)
- **Lightweight RAG without Vector Overhead:** Given the 8-page scope of `politicas_da_loja.pdf`, a dedicated vector store (e.g., ChromaDB) introduces unnecessary runtime dependencies and memory pressure. 
- The system leverages `pypdf` with a keyword relevance scoring mechanism to extract authoritative policy sections (returns, guarantees, shipping deadlines) deterministically.

### 3. Agentic Execution Loop (`agent.py`)
- **Reactive Tool Calling:** Implements an iterative ReAct pattern capable of executing parallel and multi-step tool calls (e.g., searching for a product under R\$ 800 while simultaneously retrieving return policies).
- **Hybrid Deployment Engine:**
  - **Cloud:** Powered by Groq's high-throughput LPU running `llama-3.1-8b-instant` via the OpenAI Python SDK.
  - **Local Fallback:** Automatically switches to a local Ollama instance running `qwen2.5:7b-instruct-q4_K_M` if no external API key is provided.
- **Strict Anti-Hallucination Guardrails:** The system prompt explicitly forbids inventing catalog models, prices, or policies.

---

## 📁 Repository Structure

```text
├── app.py                 # Streamlit chat interface and session state manager
├── agent.py               # Agent orchestrator, ReAct loop, and tool definitions
├── tools.py               # Deterministic SQL and document parsing functions
├── requirements.txt       # Production dependencies
├── .gitignore             # Environment and cache ignore rules
├── README.md              # Technical documentation
└── data/
    ├── emporio_musica.db  # SQLite database (orders, order_items, products)
    └── politicas_da_loja.pdf # Official store manual

🛠️ Local Setup & Execution
Prerequisites
Python 3.10+

(Optional for offline execution) Ollama with qwen2.5:7b-instruct-q4_K_M

1. Clone & Environment Setup

git clone [https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git](https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git)
cd artefact-ai-engineer-case

python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

2. Configure Environment Variables
To run in cloud mode via Groq (instant response):

Bash
# Windows (PowerShell):
\$env:GROQ_API_KEY="your_groq_api_key_here"

# Linux/macOS:
export GROQ_API_KEY="your_groq_api_key_here"
Note: If no key is set, the application will default to your local Ollama instance (http://localhost:11434/v1).

3. Run the Application
Bash
streamlit run app.py
Open your browser at http://localhost:8501.
