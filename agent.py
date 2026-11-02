import json
import os
from openai import BadRequestError, OpenAI
import streamlit as st
from tools import buscar_produtos, consultar_pedido, consultar_politicas

# 1. Recuperação da Chave Groq
chave_groq = None
try:
    if hasattr(st, "secrets"):
        if "GROQ_API_KEY" in st.secrets:
            chave_groq = str(st.secrets["GROQ_API_KEY"]).strip()
        elif "groq_api_key" in st.secrets:
            chave_groq = str(st.secrets["groq_api_key"]).strip()
        else:
            for k, v in st.secrets.items():
                if isinstance(v, str) and v.strip().startswith("gsk_"):
                    chave_groq = v.strip()
                    break
except Exception as e:
    print(f"Aviso ao ler st.secrets: {e}")

if not chave_groq:
    chave_groq = os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")

# 2. Provedor e Seleção de Modelo
if chave_groq:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1", api_key=chave_groq
    )
    try:
        modelos_disponiveis = [m.id for m in client.models.list().data]
        prioridades = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
            "gemma2-9b-it",
        ]
        MODELO = next(
            (m for m in prioridades if m in modelos_disponiveis),
            (
                modelos_disponiveis[0]
                if modelos_disponiveis
                else "llama-3.1-8b-instant"
            ),
        )
    except Exception:
        MODELO = "llama-3.1-8b-instant"
else:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO = "qwen2.5:7b-instruct-q4_K_M"

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

# 3. Schema estrito compatível com a API da Groq
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Consulta o catálogo da loja para encontrar instrumentos musicais disponíveis. Para ver todos ou catálogo amplo, deixe o termo vazio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Nome ou categoria do instrumento (ex.: 'violão', 'guitarra', 'teclado') ou vazio '' para geral.",
                    },
                    "preco_maximo": {
                        "type": "number",
                        "description": "Preço máximo em reais (BRL).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_pedido",
            "description": "Consulta informações detalhadas de um pedido pelo ID numérico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID do pedido (ex.: '1', '2').",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_politicas",
            "description": "Consulta o manual oficial sobre frete, trocas, devoluções, prazos e garantia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duvida": {
                        "type": "string",
                        "description": "Tema da dúvida (ex.: 'prazo de devolução', 'garantia').",
                    }
                },
                "required": ["duvida"],
            },
        },
    },
]

# 4. Prompt de Sistema
SYSTEM_PROMPT = """
Você é o atendente virtual oficial da 'Empório da Música', fundada em 2008 em Campo Grande/MS.

REGRAS FUNDAMENTAIS:
1. NUNCA invente instrumentos, preços, status de pedidos ou políticas.
2. Para perguntas sobre instrumentos ou catálogo: use SEMPRE a ferramenta `buscar_produtos`. Se o cliente perguntar de forma ampla ("quais outros instrumentos vocês têm?"), use termo="".
3. Se decidir chamar uma ferramenta, NÃO escreva nenhum texto conversacional antes da chamada. Apenas chame a ferramenta.
4. Escopo: Vendemos EXCLUSIVAMENTE instrumentos musicais (cordas, teclas, sopro, percussão). Não vendemos acessórios (cabos, palhetas, correias, amplificadores).
"""


# 5. Loop Reativo Resiliente
def responder_mensagem(
    historico_mensagens: list, max_iteracoes: int = 4
) -> str:
    if not chave_groq and os.environ.get("STREAMLIT_SERVER_PORT"):
        return "⚠️ Configuração pendente: Adicione a chave GROQ_API_KEY nos Secrets do Streamlit Cloud."

    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + (
        historico_mensagens
    )

    iteracao = 0
    while iteracao < max_iteracoes:
        iteracao += 1

        try:
            resposta = client.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.0,
            )
        except BadRequestError as e:
            # Fallback seguro: se a Groq falhar ao tentar montar a tool call (400),
            # pede uma resposta conversacional direta sem derrubar o chat
            print(f"[Aviso Groq Tool Calling] {e}. Executando fallback direto.")
            resposta = client.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                temperature=0.0,
            )
            return resposta.choices[0].message.content

        mensagem_assistente = resposta.choices[0].message

        if not mensagem_assistente.tool_calls:
            return mensagem_assistente.content

        mensagens.append(mensagem_assistente)

        for tool_call in mensagem_assistente.tool_calls:
            nome_funcao = tool_call.function.name
            try:
                argumentos = (
                    json.loads(tool_call.function.arguments)
                    if tool_call.function.arguments
                    else {}
                )
            except Exception:
                argumentos = {}

            funcao_python = MAPA_TOOLS.get(nome_funcao)
            if funcao_python:
                try:
                    resultado = funcao_python(**argumentos)
                except Exception as e:
                    resultado = (
                        f"Erro ao executar ferramenta {nome_funcao}: {str(e)}"
                    )
            else:
                resultado = (
                    f"Erro: Ferramenta '{nome_funcao}' não implementada."
                )

            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(resultado),
                }
            )

    return "Desculpe, o processamento excedeu o limite de passos para esta consulta."
