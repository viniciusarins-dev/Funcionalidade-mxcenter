"""
Cliente do webservice oficial NFeDistribuicaoDFe (SEFAZ).

Dado apenas a chave de acesso de 44 dígitos e o certificado digital (.pfx)
da empresa, consulta diretamente a SEFAZ (operação `consChNFe`) e devolve
o XML completo da nota (com itens), sem depender de nenhum sistema
intermediário (WTTI ou qualquer outro ERP).

Limitações importantes (documentadas também no README):
- Só funciona com a CHAVE DE ACESSO completa (44 dígitos). A operação
  consChNFe não existe "por número de NF" — a SEFAZ só indexa por chave,
  que é única nacionalmente. Se o operador digitar só o número curto da
  nota, essa consulta não tem como funcionar; nesse caso, uma fonte
  alternativa (XML local, por exemplo) precisa cobrir esse caso.
- A SEFAZ limita quantas vezes a MESMA chave pode ser consultada em um
  intervalo curto de tempo (para evitar uso indevido do serviço). O cache
  do app.py já ajuda a não bater na SEFAZ repetidamente pela mesma nota.
- O CNPJ usado na consulta precisa ser o mesmo CNPJ do certificado digital,
  e precisa ser uma das partes envolvidas na nota (emitente, destinatário
  etc.) — como a empresa é a EMITENTE das notas, isso já é atendido
  naturalmente.
"""

import base64
import gzip
import io
import logging
import xml.etree.ElementTree as ET

import requests
from requests_pkcs12 import post as post_pkcs12

import config

logger = logging.getLogger("sefaz_client")
logging.basicConfig(level=logging.INFO)


class NotaNaoEncontrada(Exception):
    pass


class ErroSefaz(Exception):
    pass


# Endpoints oficiais do webservice de Distribuição de DF-e (ambiente nacional,
# único para todo o país — não depende da UF de quem emitiu a nota).
URL_PRODUCAO = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"
URL_HOMOLOGACAO = "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

SOAP_ACTION = "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"

UF_CODIGO_POR_SIGLA = {
    'RO':'11','AC':'12','AM':'13','RR':'14','PA':'15','AP':'16','TO':'17',
    'MA':'21','PI':'22','CE':'23','RN':'24','PB':'25','PE':'26','AL':'27','SE':'28','BA':'29',
    'MG':'31','ES':'32','RJ':'33','SP':'35',
    'PR':'41','SC':'42','RS':'43',
    'MS':'50','MT':'51','GO':'52','DF':'53',
}


def _strip_namespaces(elem):
    """Remove namespaces dos nomes das tags, pra poder usar find()/findall()
    sem precisar declarar os namespaces do NFe/SOAP em todo lugar."""
    for el in elem.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return elem


def _cuf_autor(chave):
    if config.UF_EMPRESA:
        cuf = UF_CODIGO_POR_SIGLA.get(config.UF_EMPRESA.upper())
        if cuf:
            return cuf
    # fallback: deriva da própria chave (os 2 primeiros dígitos = UF do emitente)
    return chave[:2]


def _montar_envelope(chave):
    tp_amb = "1" if config.AMBIENTE == "producao" else "2"
    cuf_autor = _cuf_autor(chave)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
  <soap:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg><distDFeInt versao="1.01" xmlns="http://www.portalfiscal.inf.br/nfe"><tpAmb>{tp_amb}</tpAmb><cUFAutor>{cuf_autor}</cUFAutor><CNPJ>{config.EMPRESA_CNPJ}</CNPJ><consChNFe><chNFe>{chave}</chNFe></consChNFe></distDFeInt></nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap:Body>
</soap:Envelope>""".encode("utf-8")


def _url_ambiente():
    return URL_PRODUCAO if config.AMBIENTE == "producao" else URL_HOMOLOGACAO


def _chamar_sefaz(chave):
    envelope = _montar_envelope(chave)
    headers = {
        "Content-Type": f'application/soap+xml; charset=utf-8; action="{SOAP_ACTION}"',
    }

    try:
        resp = post_pkcs12(
            _url_ambiente(),
            data=envelope,
            headers=headers,
            pkcs12_filename=config.CERT_PATH,
            pkcs12_password=config.CERT_PASSWORD,
            timeout=config.SEFAZ_TIMEOUT,
        )
    except requests.exceptions.SSLError as e:
        raise ErroSefaz(
            f"Falha na autenticação com o certificado digital (senha errada ou "
            f"certificado inválido/expirado): {e}"
        )
    except requests.exceptions.RequestException as e:
        raise ErroSefaz(f"Falha de conexão com a SEFAZ: {e}")

    if resp.status_code != 200:
        raise ErroSefaz(f"SEFAZ respondeu HTTP {resp.status_code}: {resp.text[:300]}")

    return resp.content


def _extrair_itens_do_xml(xml_bytes):
    root = _strip_namespaces(ET.fromstring(xml_bytes))

    inf_nfe = root.find(".//infNFe")
    if inf_nfe is None:
        raise ErroSefaz("XML retornado pela SEFAZ não contém infNFe (formato inesperado).")

    chave_completa = (inf_nfe.get("Id") or "").replace("NFe", "")

    nnf_el = root.find(".//ide/nNF")
    n_nf = nnf_el.text.strip() if nnf_el is not None else ""

    dest_el = root.find(".//dest/xNome")
    cliente = dest_el.text.strip() if dest_el is not None else "Cliente não identificado"

    itens = []
    for det in root.findall(".//det"):
        prod = det.find("prod")
        if prod is None:
            continue
        xprod = prod.find("xProd")
        qcom = prod.find("qCom")
        ucom = prod.find("uCom")
        if xprod is None or qcom is None:
            continue
        try:
            qtd = float(qcom.text.replace(",", "."))
        except (TypeError, ValueError):
            qtd = 0
        itens.append({
            "produto": xprod.text.strip() if xprod.text else "Produto sem descrição",
            "qtd": round(qtd, 2),
            "unidade": (ucom.text.strip().upper() if ucom is not None and ucom.text else "UN"),
        })

    return {
        "chave": chave_completa,
        "nNF": n_nf,
        "cliente": cliente,
        "itens": itens,
    }


def consultar_por_chave(chave):
    """
    Ponto de entrada principal. Recebe a chave de 44 dígitos e devolve o
    dicionário no mesmo contrato usado pelo front-end:
    { chave, nNF, cliente, itens: [{produto, qtd, unidade}] }
    """
    if not (len(chave) == 44 and chave.isdigit()):
        raise ErroSefaz(
            "A consulta à SEFAZ só funciona com a chave de acesso completa "
            "(44 dígitos), não com o número curto da NF."
        )

    resposta_bruta = _chamar_sefaz(chave)
    root = _strip_namespaces(ET.fromstring(resposta_bruta))

    cstat_el = root.find(".//cStat")
    xmotivo_el = root.find(".//xMotivo")
    cstat = cstat_el.text if cstat_el is not None else None
    xmotivo = xmotivo_el.text if xmotivo_el is not None else "Motivo não informado"

    logger.info("Resposta SEFAZ: cStat=%s xMotivo=%s", cstat, xmotivo)

    if cstat == "137":
        raise NotaNaoEncontrada(f"Nenhum documento localizado para a chave {chave}.")

    if cstat != "138":
        # 656 = consumo indevido (throttling), outros = erro de cert/CNPJ/schema etc.
        raise ErroSefaz(f"SEFAZ recusou a consulta (cStat={cstat}): {xmotivo}")

    doc_zip_el = root.find(".//docZip")
    if doc_zip_el is None or not doc_zip_el.text:
        raise ErroSefaz("SEFAZ indicou sucesso (cStat=138) mas não retornou docZip.")

    bruto_gzip = base64.b64decode(doc_zip_el.text)
    xml_nfe = gzip.GzipFile(fileobj=io.BytesIO(bruto_gzip)).read()

    return _extrair_itens_do_xml(xml_nfe)
