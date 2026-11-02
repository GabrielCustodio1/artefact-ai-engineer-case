import json
from openai import OpenAI
from tools import buscar_produtos, consultar_pedido, consultar_politicas

# 1. Configuração Direta com Ollama Local
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODELO = "qwen2.5:7b-instruct-q4_K_M"

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

# 2. Definição Formal das Ferramentas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_produtos",
            "description": "Consulta o catálogo da loja para encontrar instrumentos musicais disponíveis, com filtros opcionais de termo e preço máximo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "termo": {
                        "type": "string",
                        "description": "Nome, modelo ou categoria do instrumento (ex: 'violão', 'guitarra', 'teclado') ou vazio para todos.",
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
            "description": "Consulta informações detalhadas de um pedido pelo número de identificação (ID).",
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
            "description": "Consulta o manual de políticas oficiais da loja para tirar dúvidas de frete, prazos, trocas e garantia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duvida": {
                        "type": "string",
                        "description": "Dúvida do cliente sobre as regras da loja.",
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

REGRAS OBRIGATÓRIAS:
1. NÃO INVENTE DADOS: Não invente modelos, preços, estoques ou regras de políticas. Consulte sempre as ferramentas.
2. USO DE FERRAMENTAS:
   - Perguntas sobre instrumentos ou catálogo: chame `buscar_produtos`.
   - Perguntas sobre pedidos e entregas: chame `consultar_pedido`.
   - Perguntas sobre políticas, frete, devoluções e garantias: chame `consultar_politicas`.
3. ESCOPO: Vendemos EXCLUSIVAMENTE instrumentos musicais. Não vendemos acessórios (palhetas, cordas avulsas, cabos, correias, amplificadores).
"""


# 4. Loop Reativo (Function Calling)
def responder_mensagem(
    historico_mensagens: list, max_iteracoes: int = 4
) -> str:
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
            argumentos = (
                json.loads(tool_call.function.arguments)
                if tool_call.function.arguments
                else {}
            )

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
