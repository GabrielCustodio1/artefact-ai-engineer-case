import json
import os
from openai import OpenAI
import streamlit as st
from tools import buscar_produtos, consultar_pedido, consultar_politicas

# 1. Recuperação da Chave de API
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
    print(f"Aviso ao ler segredos: {e}")

if not chave_groq:
    chave_groq = os.getenv("GROQ_API_KEY") or os.getenv("groq_api_key")

# 2. Inicialização e Teste Real do Modelo Ativo na Groq
if chave_groq:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1", api_key=chave_groq
    )

    # Lista de modelos candidatos suportados na Groq
    candidatos = [
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama-3.3-70b-versatile",
        "mixtral-8x7b-32768",
    ]

    MODELO = None
    for m in candidatos:
        try:
            # Faz um ping de teste de 1 token para validar se a conta tem acesso real
            client.chat.completions.create(
                model=m,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            MODELO = m
            print(f"✅ [Provedor Groq] Modelo validado e operacional: {MODELO}")
            break
        except Exception as err:
            print(f"ℹ️ Modelo '{m}' indisponível para esta conta ({err}).")

    if not MODELO:
        MODELO = "llama-3.1-8b-instant"
else:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO = "qwen2.5:7b-instruct-q4_K_M"
    print(f"⚠️ [Provedor Local] Ollama: {MODELO}")

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

# 3. Especificação das Ferramentas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Consulta o catálogo da loja para encontrar instrumentos musicais disponíveis. Para ver o catálogo completo ou geral, use termo='todos'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Nome ou categoria do instrumento (ex: 'violão', 'guitarra', 'teclado') ou 'todos' para ver a lista geral.",
                    },
                    "preco_maximo": {
                        "type": "number",
                        "description": "Preço máximo em reais (BRL).",
                    },
                },
                "required": ["termo"],
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
                        "description": "ID numérico do pedido (ex: '1', '2').",
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
                        "description": "Dúvida sobre as regras da loja (ex: 'prazo de devolução', 'garantia').",
                    }
                },
                "required": ["duvida"],
            },
        },
    },
]

# 4. Prompt do Sistema
SYSTEM_PROMPT = """
Você é o atendente virtual oficial da 'Empório da Música', fundada em 2008 em Campo Grande/MS.

REGRAS OBRIGATÓRIAS:
1. NÃO invente instrumentos, preços, status de pedidos ou políticas. Use sempre as ferramentas.
2. Para perguntas sobre instrumentos específicos (ex: violões, guitarras): chame buscar_produtos(termo="nome_do_instrumento").
3. Para perguntas amplas de catálogo (ex: "quais outros instrumentos vocês têm?", "o que vocês vendem?"): chame buscar_produtos(termo="todos").
4. Para pedidos: chame consultar_pedido(order_id=...).
5. Para regras da loja: chame consultar_politicas(duvida=...).
6. Se decidir chamar uma ferramenta, responda EXCLUSIVAMENTE com a chamada da ferramenta. Nunca escreva texto conversacional antes da chamada.
7. Escopo: Vendemos EXCLUSIVAMENTE instrumentos musicais. Não vendemos acessórios (palhetas, cordas avulsas, cabos, correias, amplificadores).
"""


# 5. Execução do Agente
def responder_mensagem(
    historico_mensagens: list, max_iteracoes: int = 4
) -> str:
    if not chave_groq and os.environ.get("STREAMLIT_SERVER_PORT"):
        return "⚠️ Chave GROQ_API_KEY não configurada nos Secrets do Streamlit Cloud."

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
        except Exception as erro_tool:
            print(f"[Aviso Tool Calling]: {erro_tool}. Tentando resposta direta.")
            # Se a Groq falhar na chamada da ferramenta, responde em linguagem natural real
            resposta_direta = client.chat.completions.create(
                model=MODELO,
                messages=mensagens,
                temperature=0.0,
            )
            return resposta_direta.choices[0].message.content

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

    return "Desculpe, excedi o limite de passos para responder a esta consulta."
