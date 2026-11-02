import json
import os

import streamlit as st
from openai import OpenAI
from tools import buscar_produtos, consultar_pedido, consultar_politicas

# 1. Identificação do Provedor (Groq na Nuvem vs. Ollama Local)
chave_groq = None

try:
    if "GROQ_API_KEY" in st.secrets:
        chave_groq = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

if not chave_groq:
    chave_groq = os.getenv("GROQ_API_KEY")

if chave_groq:
    print("🚀 [Provedor Ativo] Modo Nuvem: Groq (llama-3.1-8b-instant)")
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=chave_groq)
    MODELO = "llama-3.1-8b-instant"
else:
    print("⚠️ [Provedor Ativo] Chave Groq não detectada. Tentando Ollama local...")
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO = "qwen2.5:7b-instruct-q4_K_M"

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

# 2. Especificação formal das ferramentas (Function Calling Schema)
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

# 3. Prompt de Sistema
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


# 4. Loop de Execução com Tool Calling
def responder_mensagem(historico_mensagens: list, max_iteracoes: int = 4) -> str:
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + (historico_mensagens)

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

        # Se o modelo não pediu ferramentas, ele terminou a resposta final
        if not mensagem_assistente.tool_calls:
            return mensagem_assistente.content

        # Registra a decisão de chamar ferramentas no histórico
        mensagens.append(mensagem_assistente)

        # Executa todas as ferramentas solicitadas nesta rodada
        for tool_call in mensagem_assistente.tool_calls:
            nome_funcao = tool_call.function.name
            argumentos = json.loads(tool_call.function.arguments)

            print(f"🔧 [Tool Call] O modelo acionou: {nome_funcao}({argumentos})")

            funcao_python = MAPA_TOOLS.get(nome_funcao)
            if funcao_python:
                try:
                    resultado = funcao_python(**argumentos)
                except Exception as e:
                    resultado = f"Erro ao executar ferramenta {nome_funcao}: {e!s}"
            else:
                resultado = f"Erro: Ferramenta '{nome_funcao}' não implementada."

            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(resultado),
                }
            )

    return "Desculpe, o processamento excedeu o limite de passos para esta consulta."
