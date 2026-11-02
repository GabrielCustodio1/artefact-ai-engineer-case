import re
import sqlite3
import unicodedata
from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "emporio_musica.db"

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
    """Consulta o catálogo da loja aplicando normalização de termos, ordenação e verificação precisa de orçamento/estoque."""
    direcao_ordem = "ASC"
    termo_limpo = ""

    if termo:
        termo_norm = remover_acentos(termo)

        # 1. Detecta direção de ordenação (maior vs menor preço)
        if re.search(r"\b(caro|caros|cara|caras|maior|alto)\b", termo_norm):
            direcao_ordem = "DESC"

        # 2. Remove expressões específicas de preço baixo sem remover o instrumento 'baixo'
        termo_norm = re.sub(r"\b(pre[cç]o|valor|mais)\s+baix[oa]s?\b", "", termo_norm)

        # 3. Stopwords estritas (nunca incluir 'baixo', 'alto' ou nomes de instrumentos aqui)
        stopwords = {
            "mais",
            "barato",
            "barata",
            "baratos",
            "baratas",
            "menor",
            "maior",
            "caro",
            "cara",
            "caros",
            "caras",
            "preco",
            "precos",
            "valor",
            "valores",
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
            "instrumentos",
        }

        palavras = re.findall(r"\b\w+\b", termo_norm)
        palavras_relevantes = [p for p in palavras if p not in stopwords]
        termo_limpo = " ".join(palavras_relevantes)

    with sqlite3.connect(DB_PATH) as conn:
        conn.create_function("unaccent", 1, remover_acentos)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1. Busca produtos ativos, em estoque e dentro do orçamento (se informado)
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
                    f"Categoria: {row['category_name']} | Estoque: {row['stock_quantity']} un."
                )
            return "\n".join(resultado)

        # 2. Diagnóstico de Fallback:
        # Caso A: Produto existe e está em estoque, mas custa mais que o preço_maximo solicitado
        if preco_maximo is not None and termo_limpo:
            query_acima = """
                SELECT p.name, p.price_brl, p.stock_quantity, c.category_name
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                WHERE p.status = 'active' AND p.stock_quantity > 0 AND p.price_brl > ?
                  AND (unaccent(p.name) LIKE ? OR unaccent(p.description) LIKE ? OR unaccent(c.category_name) LIKE ?)
                ORDER BY p.price_brl ASC
                LIMIT 5
            """
            cursor.execute(
                query_acima,
                [
                    preco_maximo,
                    f"%{termo_limpo}%",
                    f"%{termo_limpo}%",
                    f"%{termo_limpo}%",
                ],
            )
            acima = cursor.fetchall()

            if acima:
                itens_acima = [
                    f"- {row['name']} | Preço: R$ {row['price_brl']:.2f} (Estoque: {row['stock_quantity']} un.)"
                    for row in acima
                ]
                return (
                    f"Não encontramos modelos de '{termo_limpo}' dentro do orçamento de até R$ {preco_maximo:.2f}. "
                    f"Os modelos disponíveis em estoque possuem valores superiores:\n"
                    + "\n".join(itens_acima)
                )

        # Caso B: Produto existe no catálogo, mas está com estoque zerado ou status inativo
        if termo_limpo:
            query_indisponiveis = """
                SELECT p.name, p.price_brl, p.stock_quantity, p.status
                FROM products p
                JOIN categories c ON p.category_id = c.category_id
                WHERE (unaccent(p.name) LIKE ? OR unaccent(p.description) LIKE ? OR unaccent(c.category_name) LIKE ?)
                  AND (p.stock_quantity = 0 OR p.status != 'active')
                LIMIT 5
            """
            cursor.execute(query_indisponiveis, [f"%{termo_limpo}%"] * 3)
            indisponiveis = cursor.fetchall()

            if indisponiveis:
                itens_indisp = [
                    f"- {row['name']} (Estoque: {row['stock_quantity']} un. - Status: {row['status']})"
                    for row in indisponiveis
                ]
                return (
                    f"O produto correspondente a '{termo_limpo}' foi localizado no catálogo, mas encontra-se esgotado ou inativo no momento:\n"
                    + "\n".join(itens_indisp)
                )

    return "Nenhum produto encontrado com os critérios informados."


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


def consultar_politicas(duvida: str) -> str:
    """Consulta as regras oficiais da loja (frete, trocas, devoluções, horários, endereço e garantia)."""
    if not PDF_PATH.exists():
        return "O arquivo de políticas da loja não foi encontrado no caminho esperado."

    reader = PdfReader(PDF_PATH)
    duvida_norm = remover_acentos(duvida)
    termos = [p for p in re.findall(r"\b\w+\b", duvida_norm) if len(p) >= 3]

    paginas_relevantes = []
    for i, pagina in enumerate(reader.pages):
        texto = pagina.extract_text() or ""
        texto_norm = remover_acentos(texto)

        pontuacao = sum(1 for termo in termos if termo in texto_norm)
        paginas_relevantes.append((pontuacao, i + 1, texto.strip()))

    paginas_relevantes.sort(key=lambda x: x[0], reverse=True)

    selecionadas = [p for p in paginas_relevantes if p[0] > 0]
    if not selecionadas:
        selecionadas = paginas_relevantes[:2]

    resultado = []
    for _, num_pag, texto in selecionadas[:2]:
        linhas_limpas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
        resultado.append(f"[Página {num_pag}]:\n" + "\n".join(linhas_limpas))

    return "\n\n---\n\n".join(resultado)
