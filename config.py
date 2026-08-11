"""
Configuração da API de conferência de pedidos (WTTI).

Tudo que muda de ambiente para ambiente (URLs, credenciais, seletores)
fica aqui, lido de variáveis de ambiente (.env). Nada disso deve ser
hardcoded dentro do scraper ou do app.py.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # carrega o arquivo .env se existir


def _env(key, default=None, required=False):
    val = os.environ.get(key, default)
    if required and not val:
        raise RuntimeError(f"Variável de ambiente obrigatória não definida: {key}")
    return val


# --- Sistema WTTI (caminho ativo — Selenium) ---------------------------
WTTI_BASE_URL = _env("WTTI_BASE_URL", "https://mxcenter.wtti.app")
WTTI_LOGIN_URL = _env("WTTI_LOGIN_URL", f"{WTTI_BASE_URL}/Login.aspx")
WTTI_SEARCH_URL = _env("WTTI_SEARCH_URL", f"{WTTI_BASE_URL}/View/Cadastro/Notas.aspx")
WTTI_USER = _env("WTTI_USER", required=True)
WTTI_PASS = _env("WTTI_PASS", required=True)

# --- Selenium ---------------------------------------------------------
HEADLESS = _env("HEADLESS", "true").lower() == "true"
IMPLICIT_WAIT_SECONDS = int(_env("IMPLICIT_WAIT_SECONDS", "0"))  # manter 0, usar waits explícitos
EXPLICIT_WAIT_SECONDS = int(_env("EXPLICIT_WAIT_SECONDS", "15"))

# --- Seletores da tela de LOGIN (validados em 2026-08-11 com testar_login.py) --------
SEL_LOGIN_USERNAME = _env("SEL_LOGIN_USERNAME", "#txtUsuario")
SEL_LOGIN_PASSWORD = _env("SEL_LOGIN_PASSWORD", "#txtSenha")
SEL_LOGIN_SUBMIT = _env("SEL_LOGIN_SUBMIT", "#btnAcessar")
SEL_LOGIN_SUCESSO = _env("SEL_LOGIN_SUCESSO", "#lblTelefone")  # elemento que só existe pós-login

# --- Seletores da tela de CONSULTA DE NOTA (AJUSTAR) -------------------
SEL_BUSCA_INPUT = _env("SEL_BUSCA_INPUT", "#ctl00_ContentPlaceHolder1_pesquisaApplet_ctl03_txtValor")
SEL_BUSCA_SUBMIT = _env("SEL_BUSCA_SUBMIT", "#btnConsultar")
SEL_RESULTADO_IFRAME = _env("SEL_RESULTADO_IFRAME", "")  # deixe vazio se não houver iframe

# Filtro "Tipo de Documento" — dropdown customizado de checkboxes (não é um
# <select>). A busca só retorna linhas se esse filtro estiver marcado, então
# o scraper abre o dropdown e marca essa opção antes de pesquisar.
SEL_TIPO_DOC_DROPDOWN = _env("SEL_TIPO_DOC_DROPDOWN", "#ctl00_ContentPlaceHolder1_pesquisaApplet_ctl02_ddlValor_sl")
SEL_TIPO_DOC_CHECKBOX = _env("SEL_TIPO_DOC_CHECKBOX", "#ctl00_ContentPlaceHolder1_pesquisaApplet_ctl02_ddlValor_14")

# Grid de resultados da busca (gdwNotas): pode listar mais de um documento
# (NF-e, CT-e, etc.) pro mesmo número. Escolhemos a linha cujo texto de
# "Tipo" bate com TIPO_NOTA_DESEJADO e clicamos no botão Selecionar dela.
SEL_TABELA_NOTAS = _env("SEL_TABELA_NOTAS", "#gdwNotas")
TIPO_NOTA_DESEJADO = _env("TIPO_NOTA_DESEJADO", "Nota Fiscal Eletrônica de Saída")

SEL_CLIENTE_NOME = _env("SEL_CLIENTE_NOME", "#txtRazaoSocial")
SEL_NUMERO_NF = _env("SEL_NUMERO_NF", "#txtNF")
SEL_TABELA_ITENS = _env("SEL_TABELA_ITENS", "#gdwProduto")
SEL_LINHAS_ITENS = _env("SEL_LINHAS_ITENS", "#gdwProduto tbody tr")
# Dentro de cada linha, índice das colunas (0-based) — AJUSTAR conforme o grid real.
# O grid gdwProduto não tem coluna de unidade; a unidade é sempre "UN" (ver scraper.py).
COL_CODIGO = int(_env("COL_CODIGO", "0"))
COL_PRODUTO = int(_env("COL_PRODUTO", "1"))
COL_QTD = int(_env("COL_QTD", "2"))

# Galeria de imagens na tela de Cadastro de Produtos
# (View/Cadastro/CadastroProduto.aspx?UID=<codigo>). Cada imagem é um
# div.galleryItem com o atributo data-src apontando pro arquivo.
SEL_GALERIA_ITEM = _env("SEL_GALERIA_ITEM", ".galeriaImagens .galleryItem")

# --- Relatório de Ranking de Produtos (saída/vendas do mês) — validado
# em 2026-08-11. Tela: View/Relatorio/RelatorioRankingProdutos.aspx.
# Usa o controle Microsoft ReportViewer — o HTML da tabela renderizada
# tem classes CSS geradas por sessão, não confiável pra seletor fixo. Em
# vez de ler a tela, o scraper preenche Data Inicial/Final, exporta o
# relatório pra Excel (.xlsx real, confirmado — não é HTML disfarçado) e
# lê o arquivo baixado com openpyxl (ver _buscar_saida_mes_produto_interno
# em scraper.py).
WTTI_RANKING_URL = _env("WTTI_RANKING_URL", f"{WTTI_BASE_URL}/View/Relatorio/RelatorioRankingProdutos.aspx")
SEL_RANKING_DATA_INICIAL = _env("SEL_RANKING_DATA_INICIAL", "#ctl00_ContentPlaceHolder1_relatorioApplet_ctl07_txtValor")
SEL_RANKING_DATA_FINAL = _env("SEL_RANKING_DATA_FINAL", "#ctl00_ContentPlaceHolder1_relatorioApplet_ctl08_txtValor")
SEL_RANKING_SUBMIT = _env("SEL_RANKING_SUBMIT", "#btnConsultar")
# Ícone que abre o menu de exportação (Excel/PDF/Word) do ReportViewer.
# O link "Excel" dentro do menu não tem id (gerado em runtime) — o
# scraper localiza ele pelo texto visível, não por seletor CSS.
SEL_RANKING_EXPORT_BOTAO = _env(
    "SEL_RANKING_EXPORT_BOTAO",
    "#ctl00_ContentPlaceHolder1_relatorioApplet_reportView_ctl05_ctl04_ctl00_ButtonImg",
)
# Texto exato do cabeçalho das colunas no Excel exportado (não índice —
# mais robusto a reordenação de colunas no relatório).
COL_RANKING_CODIGO_NOME = _env("COL_RANKING_CODIGO_NOME", "Cod Produto")
COL_RANKING_QTD_NOME = _env("COL_RANKING_QTD_NOME", "Qtd.")

# --- Tela de Manutenção de Estoque por Filial (validado em 2026-08-11
# com testar_reposicao.py, produto 203 = "BATENTE 16MM - SHOWA", estoque
# = 53) -------------------------------------------------------------
# O número que essa tela mostra pode estar desatualizado em relação à
# contagem física real — por isso a sidebar de reposição também deixa
# digitar o estoque contado à mão pra comparar com o valor do sistema.
WTTI_ESTOQUE_URL = _env("WTTI_ESTOQUE_URL", f"{WTTI_BASE_URL}/View/Cadastro/ManutencaoEstoqueFilial.aspx")
SEL_ESTOQUE_BUSCA_INPUT = _env("SEL_ESTOQUE_BUSCA_INPUT", "#txtCodProduto")
SEL_ESTOQUE_BUSCA_SUBMIT = _env("SEL_ESTOQUE_BUSCA_SUBMIT", "#btnPesquisa")
SEL_ESTOQUE_TABELA = _env("SEL_ESTOQUE_TABELA", "#gdwVendas")
SEL_ESTOQUE_LINHAS = _env("SEL_ESTOQUE_LINHAS", "#gdwVendas tbody tr")
COL_ESTOQUE_CODIGO = int(_env("COL_ESTOQUE_CODIGO", "0"))  # AJUSTAR se o furo não bater — não confirmado explicitamente
COL_ESTOQUE_QTD = int(_env("COL_ESTOQUE_QTD", "2"))

# --- API ---------------------------------------------------------------
API_KEY = _env("API_KEY", "")  # se vazio, autenticação por chave fica desabilitada
CORS_ORIGINS = _env("CORS_ORIGINS", "*")  # em produção, restrinja ao domínio do front-end
CACHE_TTL_SECONDS = int(_env("CACHE_TTL_SECONDS", "300"))  # 5 min
PORT = int(_env("PORT", "5000"))
