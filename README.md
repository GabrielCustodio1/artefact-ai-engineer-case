# Empório da Música - Local-First AI Customer Support Agent
### Technical Case: AI Engineer – Full-Stack para Aplicações com IA Generativa | Artefact Brazil

An autonomous, enterprise-grade conversational AI assistant developed for **Empório da Música**, a specialized musical instrument store founded in 2008 in Campo Grande/MS. 

Built with a **Local-First (Self-Hosted) Architecture**, the system processes structured inventory and customer order records from SQLite, extracts corporate policies from unstructured PDF documentation, and interacts with customers via an intuitive Streamlit interface—operating with **zero external cloud API dependencies, zero token costs, and 100% data privacy**.

---

## 🏛️ System Architecture

Following Artefact's core case guideline—**"solve it in the simplest way possible"**—the solution avoids artificial complexity (such as standing vector databases or bloated multi-agent frameworks) in favor of deterministic, observable, and maintainable software components:

                  ┌────────────────────────────────────────┐
                  │        Streamlit Web Interface         │
                  │               (app.py)                 │
                  └──────────────────┬─────────────────────┘
                                     │ User Query
                                     ▼
                  ┌────────────────────────────────────────┐
                  │       Agentic Controller (agent.py)    │
                  │  (Local ReAct Loop via OpenAI SDK)     │
                  └─────────┬────────────────────┬─────────┘
                            │                    │
              Tool Calling  ▼                    ▼ Tool Calling
    ┌────────────────────────────────┐   ┌────────────────────────────────┐
    │   buscar_produtos(termo, ...)  │   │   consultar_politicas(duvida)  │
    │   consultar_pedido(order_id)   │   │       (Unstructured RAG)       │
    │    (Structured SQL Engine)     │   └───────────────┬────────────────┘
    └───────────────┬────────────────┘                   │
                    │                           pypdf Text Matcher
                    ▼                       (Zero vector-db overhead)
            SQLite Database                              │
         (emporio_musica.db)                             ▼
                                                 politicas_da_loja.pdf
                                                         │
                    ┌────────────────────────────────────┘
                    ▼
      Local Ollama Inference Engine
      (qwen2.5:7b-instruct-q4_K_M)
      Listening on localhost:11434

---

## 💡 Key Architectural Pillars

### 1. Local-First Inference & Data Sovereignty
- **Model:** `qwen2.5:7b-instruct-q4_K_M` running locally via [Ollama](https://ollama.com/).
- **Privacy:** Customer purchase history, tracking codes, and internal documents remain within the local host boundary.
- **Cost & Availability:** Zero operational cost per token; immune to public cloud rate limits, network outages, and third-party credential management issues.

### 2. Structured Relational Engine (`tools.py`)
- Direct parameter-safe interaction with `emporio_musica.db` using Python's standard `sqlite3`.
- **`buscar_produtos`:** Sanitizes conversational stop-words (e.g., *"cheapest"*, *"best"*), supports category and keyword filtering, enforces budget caps, and automatically sorts results in ascending price order (`ORDER BY price_brl ASC`).
- **`consultar_pedido`:** Performs multi-table SQL joins between `orders`, `order_items`, and `products` to retrieve complete order tracking timelines, carrier codes, and itemized summaries.

### 3. Lightweight Policy Extraction (`tools.py`)
- **`consultar_politicas`:** For an 8-page document (~3,500 words), deploying vector stores (ChromaDB/FAISS) introduces unnecessary memory bloat and platform compilation issues. 
- The engine uses `pypdf` with a keyword-frequency relevance scoring algorithm to extract authoritative policy sections (7-day right of withdrawal, warranty deadlines, shipping rules) deterministically.

### 4. ReAct Execution Loop & Guardrails (`agent.py`)
- Employs native Function Calling through the standard OpenAI client abstraction pointing to `http://localhost:11434/v1`.
- Can dispatch parallel or sequential tool invocations (e.g., retrieving guitars under R\$ 800 while simultaneously looking up return shipping policies).
- **Anti-Hallucination:** An amnesic system prompt strictly prohibits fabricating prices, models, or rules without active tool verification.
- **Business Scope:** Requests for accessories (strings, picks, cables, straps, amplifiers) are politely rejected, respecting the store's exclusive focus on instruments.

---

## 📁 Repository Structure

```text
artefact-ai-engineer-case/
├── app.py                 # Streamlit web chat UI with state retention
├── agent.py               # ReAct control loop, tool definitions & local Ollama client
├── tools.py               # Parameterized SQL database queries & pypdf policy search
├── requirements.txt       # Production dependencies (streamlit, openai, pypdf)
├── .gitignore             # Virtual environments, bytecode, and cache exclusions
├── README.md              # Technical documentation (in English)
└── data/
    ├── emporio_musica.db  # Relational database (orders, order_items, products)
    └── politicas_da_loja.pdf # Official store policy manual
````

# 🚀 Quickstart & Reproduction GuidePrerequisitesPython 3.10+Ollama installed and running

### Step 1: Download & Run the Local Model

````Bash
ollama run qwen2.5:7b-instruct-q4_K_M
````
(Once downloaded, Ollama will serve the OpenAI-compatible API on http://localhost:11434/v1).

### Step 2: Clone & Set Up the Environment

````Bash
git clone [https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git](https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git)

cd artefact-ai-engineer-case

python -m venv .venv
````
````
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
````
###Step 3: Run the Application

````Bash
streamlit run app.py
````
Open your browser at http://localhost:8501.

#👨‍💻 Candidate & Submission Info

Candidate: Gabriel Custodio de Abreu

Role: AI Engineer – Full-Stack para Aplicações com IA Generativa

Company: Artefact Brazil

Submission Date: November 2026
