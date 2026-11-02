# 🎸 Empório da Música - AI Assistant

Assistente conversacional inteligente concebido para o suporte de atendimento ao cliente da loja **Empório da Música** (fundada em 2008 em Campo Grande/MS), integrando modelos de linguagem via chamada de ferramentas (*function calling*) com bases de dados relacionais e extração de políticas em PDF.

---

## 🛠️ Arquitetura e Decisões Técnicas

* **Linguagem Principal:** Python 3.10+
* **Interface de Utilizador:** Streamlit
* **Gestão de Ferramentas e Inferência:**
  * **Modo Local (Privacidade / Offline):** Ollama executando o modelo `qwen2.5:7b-instruct-q4_K_M`.
* **Mapeamento de Ferramentas (*Tool Calling*):** O agente avalia a mensagem do utilizador e invoca as ferramentas necessárias de forma sequencial num ciclo controlado de execução.
* **Persistência Relacional:** SQLite local para produtos, clientes e histórico de encomendas.
* **Recuperação Documental:** Extração e ranqueamento léxico via `pypdf`, eliminando limites de corte de texto para assegurar respostas completas sobre horários, endereços e taxas.

---

## 🚀 Como Executar o Projeto

### 1. Clonar o Repositório
```bash
git clone [https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git](https://github.com/GabrielCustodio1/artefact-ai-engineer-case.git)
cd artefact-ai-engineer-case
```
### 2. Criar e Ativar o Ambiente Virtual
```bash
python -m venv .venv

# No Windows (PowerShell):
.venv\Scripts\Activate.ps1

# No Linux/macOS:
source .venv/bin/activate
```
### 3. Instalar Dependências
```bash
pip install -r requirements.txt
```
### 4. Inicializar a Base de Dados Local
```Bash
python init_db.py
```
### 5. Configurar o Provedor de LLM
#### Opção A — Groq API (Recomendado):
Defina a variável de ambiente:

```Bash
# Windows PowerShell:
\$env:GROQ_API_KEY="sua_chave_aqui"

# Linux/macOS:
export GROQ_API_KEY="sua_chave_aqui"
(Em alternativa, crie o ficheiro .streamlit/secrets.toml contendo GROQ_API_KEY = "sua_chave").
```
#### Opção B — Ollama (Execução 100% Local):
Sem chave configurada, o agente liga-se automaticamente ao Ollama em http://localhost:11434/v1. Certifique-se de que o serviço está ativo e o modelo descarregado:

```Bash
ollama run qwen2.5:7b-instruct-q4_K_M
```
### 6. Iniciar a Aplicação
```Bash
streamlit run app.py
```
## 🔍 Ferramentas Disponíveis
buscar_produtos: Pesquisa de instrumentos musicais com suporte a normalização de texto (sem sensibilidade a acentuação), remoção de stopwords, ordenação por preço e verificação de rutura de stock.

consultar_pedido: Localização de encomendas por ID, exibindo estado do pedido, código de rastreamento, data estimada de entrega e itens comprados.

consultar_politicas: Consulta integral das regras operacionais da loja a partir do manual em PDF (endereço físico, horários de funcionamento, regras de frete, prazos de arrependimento e garantia).

## ⚠️ Limitações Conhecidas
Execução Sequencial de Ferramentas: Quando o modelo solicita múltiplas ferramentas numa única iteração, a execução ocorre sequencialmente e não em paralelo assíncrono.

Preço Histórico de Encomendas: O esquema relacional em order_items não armazena o preço unitário histórico no momento da compra; o valor apresentado provém do catálogo atual da tabela products.

Autenticação de Pedidos: Por se tratar de um protótipo de demonstração, a consulta de encomendas não exige validação de identidade do cliente (como CPF ou e-mail vinculado).

Recuperação Léxica em PDF: A busca documental assenta em ranqueamento léxico de termos com pontuação por página, sem recurso a embeddings densos ou base de vetores, mantendo a solução leve e sem dependências de infraestrutura complexa.

## 🤖 Uso de Assistentes de IA
Durante o desenvolvimento deste desafio, assistentes de IA generativa foram utilizados para:

Refatoração de consultas SQL e otimização de funções de normalização Unicode no SQLite.

Estruturação e formatação de schemas JSON para a especificação das ferramentas no padrão OpenAI.

Revisão de casos de teste de conversação e refinamento dos blocos de tratamento de exceções da aplicação.
