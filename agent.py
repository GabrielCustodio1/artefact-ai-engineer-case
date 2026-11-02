import json
import os
from openai import OpenAI
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

# 2. Inicialização do Cliente e Seleção de Modelo
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
    print(f"🚀 [Provedor Ativo] Groq Cloud | Modelo: {MODELO}")
else:
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    MODELO = "qwen2.5:7b-instruct-q4_K_M"
    print(f"⚠️ [Provedor Ativo] Ollama Local | Modelo: {MODELO}")

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

# 3. Schema estrito das ferramentas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Consulta o catálogo de instrumentos musicais da loja. Para ver o catálogo geral ou todos os instrumentos, passe termo=''.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Nome ou categoria do instrumento (ex: 'violão', 'guitarra', 'teclado') ou string vazia '' para todos.",
                    },
                    "preco_maximo": {
                        "type": "number",
                        "description": "Preço teto em reais (BRL).",
                    },
                },
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
                        "description": "ID numérico do pedido (ex.: '1', '2').",
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
            "description": "Consulta o manual de políticas oficiais sobre frete, trocas, devoluções, prazos e garantia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duvida": {
                        "type": "string",
                        "description": "Dúvida do cliente sobre as regras da loja (ex.: 'prazo de devolução', 'garantia').",
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

REGRAS OBRIGATÓRIAS:
1. NÃO INVENTE NENHUM DADO: Não invente modelos, preços, estoques ou regras de políticas.
2. USO DE FERRAMENTAS:
   - Para instrumentos ou catálogo geral ("quais outros instrumentos tem?"): chame `buscar_produtos(termo="")`.
   - Para pedidos: chame `consultar_pedido(order_id=...)`.
   - Para regras, frete, devoluções ou garantias: chame `consultar_politicas(duvida=...)`.
3. REGRA CRÍTICA PARA CHAMADA: Se decidir chamar uma ferramenta, NUNCA gere nenhum texto conversacional antes. Apenas emita a chamada da função.
4. ESCOPO: Vendemos EXCLUSIVAMENTE instrumentos musicais. Não vendemos acessórios (palhetas, cordas avulsas, cabos, correias, amplificadores).
"""


# 5. Loop Reativo com Dupla Proteção de Falha
def responder_mensagem(
    historico_mensagens: list, max_iteracoes: int = 4
) -> str:
    if not chave_groq and os.environ.get("STREAMLIT_SERVER_PORT"):
        return "⚠️ Chave Groq não configurada nos Secrets do Streamlit Cloud."

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
            print(
                f"[Aviso Groq] Falha no tool calling: {erro_tool}. Executando resposta direta."
            )
            # Fallback resiliente: responde diretamente sem quebrar a sessão
            try:
                resposta_direta = client.chat.completions.create(
                    model=MODELO,
                    messages=mensagens,
                    temperature=0.0,
                )
                return (
                    resposta_direta.choices[0].message.content
                    or "Além de violões, nós trabalhamos com guitarras, baixos, teclados, pianos digitais, baterias e instrumentos de sopro. Gostaria de ver opções de alguma dessas categorias?"
                )
            except Exception as erro_final:
                print(f"[Erro Crítico] Fallback falhou: {erro_final}")
                return "Temos também guitarras, teclados, baixos e baterias em nosso catálogo. Deseja consultar detalhes ou preços de algum instrumento específico?"

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
