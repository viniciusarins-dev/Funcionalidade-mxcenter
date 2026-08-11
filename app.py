"""
API de Conferência de Pedidos — WTTI (via Selenium)

Expõe:
  GET /api/notas/<codigo>            -> itens da nota, buscando no WTTI
                                         (Selenium). Aceita tanto o número
                                         curto da NF (ex: "1234") quanto a
                                         chave de acesso completa (44 dígitos).
  GET /api/produtos/<codigo>/imagens -> lista de URLs de imagens do produto
                                         (galeria da tela de Cadastro de
                                         Produtos), buscado sob demanda por
                                         item pra não deixar /api/notas lento.
  GET /api/produtos/<codigo>/reposicao -> saída do mês (Relatório de Ranking
                                         de Produtos) + estoque cadastrado
                                         no sistema (Manutenção de Estoque
                                         por Filial), pra sidebar de
                                         sugestão de pedido.
  GET /api/health                    -> status simples
  POST /api/login                    -> força um novo login no WTTI (útil se
                                         a sessão expirar no meio do dia)

Contrato de resposta de /api/notas/<codigo>:
{
  "chave": "35240112345678000199550010000012341123456789",
  "nNF": "1234",
  "cliente": "Nome do Cliente",
  "itens": [
    { "codigo": "1552", "produto": "Nome do produto", "qtd": 10, "unidade": "UN" }
  ]
}

Contrato de resposta de /api/produtos/<codigo>/imagens:
{ "codigo": "1552", "imagens": ["https://mxcenter.wtti.app/Site/000182.jpg"] }

Contrato de resposta de /api/produtos/<codigo>/reposicao:
{ "codigo": "1552", "saida_mes": 106.0, "estoque_sistema": 20.0 }
(o cálculo de quantidade sugerida e a comparação com o estoque contado à
mão ficam por conta do front-end — a API só devolve os dois números crus)
"""

import time
import logging
from flask import Flask, jsonify, request, abort, send_from_directory
from flask_cors import CORS

import config
from scraper import (
    scraper,
    buscar_nota,
    buscar_imagens_produto,
    buscar_estoque_produto,
    buscar_saida_mes_produto,
    NotaNaoEncontrada,
    ProdutoNaoEncontrado,
    ErroWtti,
)

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app, origins=config.CORS_ORIGINS)

logger = logging.getLogger("app")
logging.basicConfig(level=logging.INFO)

# Cache simples em memória: evita repetir o scraping (que é relativamente
# lento, envolve abrir tela, login se necessário, etc.) se o operador
# escanear/digitar a mesma nota duas vezes em poucos minutos.
_cache = {}  # codigo -> (timestamp, dados)
_cache_imagens = {}  # codigo_produto -> (timestamp, [urls])
_cache_reposicao = {}  # codigo_produto -> (timestamp, dados)


def _buscar_com_cache(codigo):
    agora = time.time()
    if codigo in _cache:
        ts, dados = _cache[codigo]
        if agora - ts < config.CACHE_TTL_SECONDS:
            logger.info("Cache hit para %s", codigo)
            return dados

    dados = buscar_nota(codigo)
    _cache[codigo] = (agora, dados)
    return dados


def _buscar_imagens_com_cache(codigo_produto):
    agora = time.time()
    if codigo_produto in _cache_imagens:
        ts, urls = _cache_imagens[codigo_produto]
        if agora - ts < config.CACHE_TTL_SECONDS:
            logger.info("Cache hit para imagens do produto %s", codigo_produto)
            return urls

    urls = buscar_imagens_produto(codigo_produto)
    _cache_imagens[codigo_produto] = (agora, urls)
    return urls


def _buscar_reposicao_com_cache(codigo_produto):
    agora = time.time()
    if codigo_produto in _cache_reposicao:
        ts, dados = _cache_reposicao[codigo_produto]
        if agora - ts < config.CACHE_TTL_SECONDS:
            logger.info("Cache hit para reposição do produto %s", codigo_produto)
            return dados

    dados = {
        "codigo": codigo_produto,
        "saida_mes": buscar_saida_mes_produto(codigo_produto),
        "estoque_sistema": buscar_estoque_produto(codigo_produto),
    }
    _cache_reposicao[codigo_produto] = (agora, dados)
    return dados


def _checar_api_key():
    if not config.API_KEY:
        return  # autenticação desabilitada (uso interno/dev)
    chave_enviada = request.headers.get("X-API-Key", "")
    if chave_enviada != config.API_KEY:
        abort(401, description="API key inválida ou ausente (header X-API-Key).")


@app.route("/")
def tela_conferencia():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/notas/<codigo>")
def obter_nota(codigo):
    _checar_api_key()
    codigo = codigo.strip()

    if not codigo:
        return jsonify({"erro": "Código vazio"}), 400

    try:
        dados = _buscar_com_cache(codigo)
        return jsonify(dados), 200

    except NotaNaoEncontrada as e:
        logger.info("Não encontrada: %s", e)
        return jsonify({"erro": str(e)}), 404

    except ErroWtti as e:
        logger.warning("Erro WTTI: %s", e)
        return jsonify({"erro": str(e)}), 502

    except Exception as e:
        logger.exception("Erro inesperado ao buscar nota %s", codigo)
        return jsonify({"erro": f"Falha interna ao consultar o WTTI: {e}"}), 500


@app.route("/api/produtos/<codigo>/imagens")
def obter_imagens_produto(codigo):
    _checar_api_key()
    codigo = codigo.strip()

    if not codigo:
        return jsonify({"erro": "Código vazio"}), 400

    try:
        urls = _buscar_imagens_com_cache(codigo)
        return jsonify({"codigo": codigo, "imagens": urls}), 200

    except ErroWtti as e:
        logger.warning("Erro WTTI ao buscar imagens de %s: %s", codigo, e)
        return jsonify({"erro": str(e)}), 502

    except Exception as e:
        logger.exception("Erro inesperado ao buscar imagens do produto %s", codigo)
        return jsonify({"erro": f"Falha interna ao consultar o WTTI: {e}"}), 500


@app.route("/api/produtos/<codigo>/reposicao")
def obter_reposicao(codigo):
    _checar_api_key()
    codigo = codigo.strip()

    if not codigo:
        return jsonify({"erro": "Código vazio"}), 400

    try:
        dados = _buscar_reposicao_com_cache(codigo)
        return jsonify(dados), 200

    except ProdutoNaoEncontrado as e:
        logger.info("Reposição — produto não encontrado: %s", e)
        return jsonify({"erro": str(e)}), 404

    except ErroWtti as e:
        logger.warning("Erro WTTI ao buscar reposição de %s: %s", codigo, e)
        return jsonify({"erro": str(e)}), 502

    except Exception as e:
        logger.exception("Erro inesperado ao buscar reposição do produto %s", codigo)
        return jsonify({"erro": f"Falha interna ao consultar o WTTI: {e}"}), 500


@app.route("/api/login", methods=["POST"])
def forcar_login():
    """Força um novo login — útil se a sessão do WTTI expirar no meio do dia."""
    _checar_api_key()
    try:
        scraper.login(forcar=True)
        return jsonify({"status": "logado"})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=False)
