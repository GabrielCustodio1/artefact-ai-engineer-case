import json

from openai import OpenAI
from tools import buscar_produtos, consultar_pedido, consultar_politicas

# 1. Configuração do Provedor de Inferência Local (Ollama)
# Execução 100% offline e local, garantindo total privacidade dos dados
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODELO = "qwen2.5:7b-instruct-q4_K_M"

MAPA_TOOLS = {
    "buscar_produtos": buscar_produtos,
    "consultar_pedido": consultar_pedido,
    "consultar_politicas": consultar_politicas,
}

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
                        "description": "Nome, modelo ou categoria do instrumento (ex.: 'violão', 'baixo', 'guitarra', 'teclado').",
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
            "description": "Consulta o manual de políticas oficiais da loja para responder sobre endereço, horários de funcionamento, frete, trocas, devoluções, prazos e garantia.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duvida": {
                        "type": "string",
                        "description": "O tema ou dúvida sobre a regra ou informação da loja (ex.: 'horário de funcionamento', 'endereço', 'prazo de devolução', 'frete Campo Grande').",
                    }
                },
                "required": ["duvida"],
            },
        },
    },
]

SYSTEM_PROMPT = """
Você é o atendente virtual oficial da 'Empório da Música', loja fundada em 2008 em Campo Grande/MS.
Seu tom de voz é amigável, acolhedor e profissional (informal-profissional).

DIRETRIZES E REGRAS MANDATÓRIAS:
1. NUNCA INVENTE DADOS: Jamais assuma modelos, preços, prazos, estoques, endereços ou taxas. Todas as informações factuais devem provir das ferramentas.
2. USO ESTRITO DE FERRAMENTAS:
   - Para pesquisar instrumentos, marcas, valores ou disponibilidade: utilize `buscar_produtos`.
   - Para regras, prazos, custos de frete, horário de atendimento, endereço físico ou garantias: utilize `consultar_politicas`.
   - Para dados de pedidos efetuados: utilize `consultar_pedido`.
3. ESCOPO DO NEGÓCIO:
   - A loja vende EXCLUSIVAMENTE instrumentos musicais. Não comercializamos acessórios avulsos (cordas, palhetas, correias, cabos, suportes ou amplificadores). Caso o cliente solicite acessórios, explique com cortesia que focamos unicamente nos instrumentos.
   - Caso o usuário envie mensagens sobre tópicos totalmente fora de contexto (ex.: futebol, receitas, política, programação), responda com simpatia lembrando que o seu papel é exclusivamente o suporte aos clientes da Empório da Música.
"""


def responder_mensagem(historico_mensagens: list, max_iteracoes: int = 4) -> str:
    """Executa o ciclo de raciocínio e chamada sequencial de ferramentas do agente local."""
    mensagens = [{"role": "system", "content": SYSTEM_PROMPT}] + list(
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
        except Exception as erro_api:
            return (
                f"Erro na comunicação com o Ollama local: {erro_api!s}. "
                "Certifique-se de que o serviço do Ollama está rodando localmente com o modelo baixado."
            )

        mensagem_assistente = resposta.choices[0].message

        if not mensagem_assistente.tool_calls:
            return (
                mensagem_assistente.content
                or "Não foi possível gerar uma resposta no momento."
            )

        mensagens.append(mensagem_assistente)

        # Execução das ferramentas solicitadas
        for tool_call in mensagem_assistente.tool_calls:
            nome_funcao = tool_call.function.name

            try:
                argumentos = json.loads(tool_call.function.arguments)
            except (json.JSONDecodeError, TypeError) as erro_json:
                argumentos = {}
                resultado = f"Erro nos argumentos enviados pelo modelo: {erro_json!s}"
            else:
                funcao_python = MAPA_TOOLS.get(nome_funcao)
                if funcao_python:
                    try:
                        resultado = funcao_python(**argumentos)
                    except Exception as erro_exec:
                        resultado = f"Erro ao executar a ferramenta {nome_funcao}: {erro_exec!s}"
                else:
                    resultado = (
                        f"Ferramenta '{nome_funcao}' não reconhecida pelo sistema."
                    )

            mensagens.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": str(resultado),
                }
            )

    return "Desculpe, o processamento excedeu o limite de passos estabelecido para esta consulta."
