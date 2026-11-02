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
def buscar_produtos(termo: str = None, preco_maximo: float = None):
    conn = sqlite3.connect("data/emporio_musica.db")
    cursor = conn.cursor()

    query = "SELECT id, name, category, price_brl, stock_quantity FROM products WHERE 1=1"
    params = []

    # Se o termo for preenchido e diferente de 'todos', filtra pelo nome ou categoria
    if termo and termo.strip().lower() not in ["todos", "tudo", "geral", ""]:
        query += " AND (LOWER(name) LIKE ? OR LOWER(category) LIKE ?)"
        termo_sql = f"%{termo.strip().lower()}%"
        params.extend([termo_sql, termo_sql])

    if preco_maximo is not None:
        query += " AND price_brl <= ?"
        params.append(preco_maximo)

    cursor.execute(query, params)
    produtos = cursor.fetchall()
    conn.close()

    if not produtos:
        return "Nenhum instrumento encontrado com esses critérios."

    resultado = []
    for p in produtos:
        resultado.append(
            f"ID: {p[0]} | Nome: {p[1]} | Categoria: {p[2]} | Preço: R$ {p[3]:.2f} | Estoque: {p[4]}"
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
