import re
import sqlite3
import unicodedata
from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "emporio_musica.db"

# Localização do manual de políticas da loja
PDF_PATH = BASE_DIR / "data" / "politicas_da_loja.pdf"
if not PDF_PATH.exists():
    PDF_PATH = BASE_DIR / "data" / "raw_data" / "politicas_da_loja.pdf"


def remover_acentos(texto: str) -> str:
    """Remove marcas de acentuação e converte para minúsculas."""
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def buscar_produtos(termo: str = None, preco_maximo: float = None) -> str:
    """Consulta o catálogo da loja aplicando normalização de termos, ordenação por preço e verificação de stock."""
    # Lista de stopwords e termos de ordenação a remover da palavra-chave de pesquisa
    stopwords_ordenacao = {
        "mais",
        "barato",
        "barata",
        "baratos",
        "baratas",
        "menor",
        "baixo",
        "caro",
        "cara",
        "caros",
        "caras",
        "maior",
        "alto",
        "preco",
        "valor",
    }
    stopwords_gerais = {
        "de",
        "do",
        "da",
        "dos",
        "das",
        "para",
        "com",
        "um",
        "uma",
        "uns",
        "umas",
        "o",
        "a",
        "os",
        "as",
        "em",
        "no",
        "na",
        "nos",
        "nas",
        "loja",
        "instrumento",
    }

    direcao_ordem = "ASC"  # Ordenação padrão: menor preço primeiro
    termo_limpo = ""

    if termo:
        termo_norm = remover_acentos(termo)
        palavras = re.findall(r"\b\w+\b", termo_norm)

        # Deteta se há intenção explícita de ordenação
        if any(
            p in {"caro", "cara", "caros", "caras", "maior", "alto"} for p in palavras
        ):
            direcao_ordem = "DESC"

        # Filtra stopwords mantendo os termos relevantes do instrumento/modelo
        palavras_relevantes = [
            p
            for p in palavras
            if p not in stopwords_ordenacao and p not in stopwords_gerais
        ]
        termo_limpo = " ".join(palavras_relevantes)

    with sqlite3.connect(DB_PATH) as conn:
        conn.create_function("unaccent", 1, remover_acentos)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Consulta produtos ativos e disponíveis em stock
        query_ativa = """
            SELECT p.name, p.price_brl, p.stock_quantity, c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category_id = c.category_id
            WHERE p.status = 'active' AND p.stock_quantity > 0
        """
        params_ativa = []

        if preco_maximo is not None:
            query_ativa += " AND p.price_brl <= ?"
            params_ativa.append(preco_maximo)

        if termo_limpo:
            query_ativa += " AND (unaccent(p.name) LIKE ? OR unaccent(p.description) LIKE ? OR unaccent(c.category_name) LIKE ?)"
            param_like = f"%{termo_limpo}%"
            params_ativa.extend([param_like, param_like, param_like])

        query_ativa += f" ORDER BY p.price_brl {direcao_ordem} LIMIT 10"
        cursor.execute(query_ativa, params_ativa)
        linhas = cursor.fetchall()

        if linhas:
            resultado = []
            for row in linhas:
                resultado.append(
                    f"- Produto: {row['name']} | Preço: R$ {row['price_brl']:.2f} | "
                    f"Categoria: {row['category_name']} | Stock: {row['stock_quantity']} un."
                )
            return "\n".join(resultado)

        # 2. Se nada foi retornado, verifica se o item existe mas está esgotado ou inativo
        if termo_limpo:
            query_esgotados = """
                SELECT p.name, p.stock_quantity, p.status
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                WHERE (unaccent(p.name) LIKE ? OR unaccent(p.description) LIKE ? OR unaccent(c.category_name) LIKE ?)
                LIMIT 5
            """
            cursor.execute(query_esgotados, [f"%{termo_limpo}%"] * 3)
            esgotados = cursor.fetchall()

            if esgotados:
                itens_esgotados = [
                    f"- {row['name']} (Stock atual: {row['stock_quantity']} un. - Status: {row['status']})"
                    for row in esgotados
                ]
                return (
                    "O produto foi localizado no catálogo, mas encontra-se esgotado ou inativo de momento:\n"
                    + "\n".join(itens_esgotados)
                )

    return "Nenhum produto encontrado com os critérios informados."


def consultar_pedido(order_id: str) -> str:
    """Busca o estado, previsão de entrega e itens de um pedido pelo ID."""
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
            return f"Pedido #{order_id} não foi encontrado no sistema. Verifique o número digitado."

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

    detalhes = [
        f"Pedido #{pedido['order_id']}:",
        f"- Data: {pedido['order_date']}",
        f"- Estado: {pedido['status']}",
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


def consultar_politicas(duvida: str) -> str:
    """Consulta as regras oficiais da loja (frete, trocas, devoluções, horários, endereço e garantia)."""
    if not PDF_PATH.exists():
        return "O ficheiro de políticas da loja não foi encontrado no caminho esperado."

    reader = PdfReader(PDF_PATH)
    duvida_norm = remover_acentos(duvida)
    termos = [p for p in re.findall(r"\b\w+\b", duvida_norm) if len(p) >= 3]

    paginas_relevantes = []
    for i, pagina in enumerate(reader.pages):
        texto = pagina.extract_text() or ""
        texto_norm = remover_acentos(texto)

        pontuacao = sum(1 for termo in termos if termo in texto_norm)
        paginas_relevantes.append((pontuacao, i + 1, texto.strip()))

    # Ordena as páginas por relevância de pontuação
    paginas_relevantes.sort(key=lambda x: x[0], reverse=True)

    # Retorna o conteúdo integral sem truncagem a 1000 caracteres
    selecionadas = [p for p in paginas_relevantes if p[0] > 0]
    if not selecionadas:
        selecionadas = paginas_relevantes[
            :2
        ]  # Caso de salvaguarda: retorna as duas primeiras páginas

    resultado = []
    for _, num_pag, texto in selecionadas[:2]:
        linhas_limpas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
        resultado.append(f"[Página {num_pag}]:\n" + "\n".join(linhas_limpas))

    return "\n\n---\n\n".join(resultado)
