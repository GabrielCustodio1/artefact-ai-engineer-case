import json
import os
from openai import OpenAI
import streamlit as st
from tools import buscar_produtos, consultar_pedido, consultar_politicas

# 1. Recuperação Robusta da Chave Groq
chave_groq = None

# A) Tenta ler dos Secrets do Streamlit (maiúsculo, minúsculo ou varredura de valores gsk_)
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

# B) Fallback para variáveis de ambiente do sistema
if not chave_groq:
    chave_groq = os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")

# 2. Inicialização do Provedor e Seleção de Modelo
if chave_groq:
    print("🚀 [Provedor Ativo] Modo Nuvem: Groq API")
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1", api_key=chave_groq
    )

    # Identifica dinamicamente quais modelos sua conta Groq possui acesso
    try:
        modelos_disponiveis = [m.id for m in client.models.list().data]
        print(f"📋 Modelos liberados na sua conta Groq: {modelos_disponiveis}")

        preferencias = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama3-8b-8192",
            "llama3-70b-8192",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
        MODELO = next(
            (m for m in preferencias if m in modelos_disponiveis),
            (
                modelos_disponiveis[0]
                if modelos_disponiveis
                else "llama-3.1-8b-instant"
            ),
        )
    except Exception as erro_lista:
        print(f"Aviso ao consultar modelos da Groq: {erro_lista}")
        MODELO = "llama-3.1-8b-instant"

    print(f"✅ Modelo Groq selecionado para atendimento: {MODELO}")
else:
    # Se estiver rodando no Streamlit Cloud sem chave, não adianta tentar localhost
    print(
        "⚠️ [Provedor Ativo] Chave Groq não encontrada. Usando modo Ollama local."
    )
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO = "qwen2.5:7b-instruct-q4_K_M"

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

# 3. Especificação das Ferramentas (Function Calling)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Consulta o catálogo da loja para encontrar instrumentos musicais disponíveis, com filtros opcionais de termo de busca e preço máximo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Nome, modelo ou categoria do instrumento (ex.: 'violão', 'guitarra').",
                    },
                    "preco_maximo": {
                        "type": "number",
                        "description": "Valor máximo em reais (BRL) que o cliente deseja pagar.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_pedido",
            "description": "Consulta informações detalhadas de um pedido pelo número de identificação (ID), retornando status, rastreio, previsão de entrega e itens comprados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "ID numérico ou código do pedido a ser consultado (ex.: '1', '1024').",
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
            "description": "Consulta o manual de políticas oficiais da loja para responder sobre frete, trocas, devoluções, prazos e garantia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duvida": {
                        "type": "string",
                        "description": "O tema ou dúvida sobre a regra da loja (ex.: 'prazo de devolução', 'troca por defeito', 'frete').",
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

REGRAS CRÍTICAS E OBRIGATÓRIAS:
1. VOCÊ NÃO SABE O CATÁLOGO DE CABEÇA: Não invente modelos, preços, estoques ou regras de políticas. É terminantemente proibido inventar dados.
2. USO OBRIGATÓRIO DE FERRAMENTAS:
   - Perguntas de instrumentos, valores ou estoque: chame obrigatoriamente `buscar_produtos`.
   - Perguntas de regras, prazos, frete, devolução ou garantia: chame obrigatoriamente `consultar_politicas`.
   - Perguntas sobre pedidos: chame obrigatoriamente `consultar_pedido`.
3. Se a dúvida cobrir mais de um assunto, chame as ferramentas necessárias antes de responder.
4. Escopo: Vendemos EXCLUSIVAMENTE instrumentos musicais. Não vendemos acessórios (cordas avulsas, palhetas, cabos, correias, amplificadores).
"""


# 5. Loop Reativo do Agente
def responder_mensagem(
    historico_mensagens: list, max_iteracoes: int = 4
) -> str:
    # Se caiu no fallback local mas está na nuvem sem Ollama:
    if not chave_groq and os.environ.get("STREAMLIT_SERVER_PORT"):
        return (
            "⚠️ Configuração pendente: A chave da Groq não foi detectada nos Secrets do Streamlit Cloud. "
            "Por favor, acesse Settings > Secrets e adicione: GROQ_API_KEY = 'gsk_...'"
        )

    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + (
        historico_mensagens
    )

    iteracao = 0
    while iteracao < max_iteracoes:
        iteracao += 1

        resposta = client.chat.completions.create(
            model=MODELO,
            messages=mensagens,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.0,
        )

        mensagem_assistente = resposta.choices[0].message

        if not mensagem_assistente.tool_calls:
            return mensagem_assistente.content

        mensagens.append(mensagem_assistente)

        for tool_call in mensagem_assistente.tool_calls:
            nome_funcao = tool_call.function.name
            argumentos = json.loads(tool_call.function.arguments)

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
