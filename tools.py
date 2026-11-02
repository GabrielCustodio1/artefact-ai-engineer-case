import sqlite3
from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(__file__).resolve().parent / "data" / "emporio_musica.db"

# Procura pelo PDF de políticas da empresa
PDF_PATH = BASE_DIR / "data" / "politicas_da_loja.pdf"
if not PDF_PATH.exists():
    PDF_PATH = BASE_DIR / "data" / "raw_data" / "politicas_da_loja.pdf"


# Funcao de busca de informacoes dos produtos
def buscar_produtos(termo: str = None, preco_maximo: float = None) -> str:
    # query base e uma lista vazia de parâmetros
    query = """
        SELECT p.name, p.price_brl, p.stock_quantity, c.category_name, p.description
        FROM products p
        JOIN categories c ON p.category_id = c.category_id
        WHERE p.status = 'active' AND p.stock_quantity > 0
    """
    params = []

    # Se o usuário passou um preço máximo, adicionamos a condição:
    if preco_maximo is not None:
        query += " AND p.price_brl <= ?"
        params.append(preco_maximo)

    # Se o usuário passou um termo de busca, procuramos com 'LIKE' (busca por aproximação)
    if termo:
        query += (
            " AND (p.name LIKE ? OR p.description LIKE ? OR c.category_name LIKE ?)"
        )
        termo_busca = f"%{termo}%"
        params.extend([termo_busca, termo_busca, termo_busca])

    # Limitamos o resultado para não sobrecarregar o prompt da LLM
    query += " LIMIT 10"

    # Formatacao da busca para facilitar a leitura da LLM
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        linhas = cursor.fetchall()

    if not linhas:
        return "Nenhum produto encontrado com os critérios informados."

    # Formata o resultado em linhas amigáveis
    resultado = []
    for row in linhas:
        resultado.append(
            f"- Produto: {row['name']} | Preço: R$ {row['price_brl']:.2f} | "
            f"Categoria: {row['category_name']} | Estoque: {row['stock_quantity']} un."
        )

    return "\n".join(resultado)


# Funcao de busca de informacao do pedido do cliente
def consultar_pedido(order_id: str) -> str:
    """Busca o status, previsão de entrega e itens de um pedido pelo ID."""
    order_id = str(order_id).strip()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT order_id, order_date, status, tracking_code, estimated_delivery, total_brl
            FROM orders
            WHERE order_id = ?
        """,
            (order_id,),
        )
        pedido = cursor.fetchone()

        if not pedido:
            return f"Pedido #{order_id} não foi encontrado no sistema. Verifique o número digitado"

        # Busca os itens desse pedido cruzando com a tabela products
        cursor.execute(
            """
            SELECT p.name, oi.quantity, p.price_brl
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = ?
        """,
            (order_id,),
        )
        itens = cursor.fetchall()

    # Monta o texto de resposta estruturado para a LLM
    detalhes = [
        f"Pedido #{pedido['order_id']}:",
        f"- Data: {pedido['order_date']}",
        f"- Status: {pedido['status']}",
        f"- Rastreio: {pedido['tracking_code'] if pedido['tracking_code'] else 'Ainda não disponível'}",
        f"- Previsão de entrega: {pedido['estimated_delivery'] if pedido['estimated_delivery'] else 'A calcular'}",
        f"- Total: R$ {pedido['total_brl']:.2f}",
        "- Itens comprados:",
    ]

    for item in itens:
        detalhes.append(
            f"  * {item['quantity']}x {item['name']} (R$ {item['price_brl']:.2f} un.)"
        )

    return "\n".join(detalhes)


# Funcao de pesquisa de politicas da loja
def consultar_politicas(duvida: str) -> str:
    """Consulta as regras oficiais da loja (frete, trocas, devolucoes, prazos e garantia)."""
    if not PDF_PATH.exists():
        return "O arquivo de politicas da loja nao foi encontrado no caminho esperado."

    reader = PdfReader(PDF_PATH)
    # foca em palavras mais longas, com maior significacao
    termos = [p.lower() for p in duvida.split() if len(p) >= 4]

    paginas_relevantes = []
    for i, pagina in enumerate(reader.pages):
        texto = pagina.extract_text() or ""
        texto_lower = texto.lower()

        # pontua a pagina dependendo do numero de termos contidos tanto na pagina, quanto na duvida do cliente
        pontuacao = sum(1 for termo in termos if termo in texto_lower)
        if pontuacao > 0:
            paginas_relevantes.append((pontuacao, i + 1, texto.strip()))

    # Caso nenhum termo for encontrado
    if not paginas_relevantes:
        p1 = reader.pages[0].extract_text() or ""
        return f"[Pagina 1 - Visao Geral]:\n{p1[:1000]}"

    # Pega a pagina com maior relevancia
    paginas_relevantes.sort(key=lambda x: x[0], reverse=True)

    # Retorna o conteudo das paginas mais relevantes
    resultado = []
    for _, num_pag, texto in paginas_relevantes[:2]:
        texto_limpo = " ".join(texto.split())
        resultado.append(f"[Pagina {num_pag}]:\n{texto_limpo[:1000]}")
    return "\n\n---\n\n".join(resultado)
