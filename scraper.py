"""
Scraper do sistema WTTI (mxcenter.wtti.app) via Selenium.

Este módulo reaproduz, de forma genérica, os mesmos cuidados que
normalmente são necessários em sistemas ASP.NET WebForms antigos:
  - esperas explícitas (nunca time.sleep fixo como estratégia principal)
  - reentrada em caso de StaleElementReferenceException após postback
  - troca segura de iframe, quando existir
  - retries curtos em cliques de modal/botão
  - recuperação automática se o navegador travar/crashar no meio de uma busca
  - captura de screenshot + HTML da página no momento do erro, salvos em
    debug_screenshots/, pra diagnosticar problema de seletor sem precisar
    reproduzir manualmente

Os pontos marcados com "AJUSTAR" são os únicos que dependem do HTML
real do WTTI e provavelmente vão precisar de ajuste fino depois de
inspecionar a tela de consulta de nota com o DevTools do navegador.
"""

import os
import time
import threading
import logging
import datetime
from functools import wraps

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
    WebDriverException,
)

import config

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho",
    7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

logger = logging.getLogger("wtti_scraper")
logging.basicConfig(level=logging.INFO)

DEBUG_DIR = "debug_screenshots"


def retry_em_stale(tentativas=3, espera=0.4):
    """
    Decorator para lidar com StaleElementReferenceException, comum logo
    após um postback do ASP.NET recriar o DOM enquanto ainda estamos
    segurando uma referência ao elemento antigo.
    """
    def decorador(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ultimo_erro = None
            for tentativa in range(1, tentativas + 1):
                try:
                    return func(*args, **kwargs)
                except (StaleElementReferenceException, ElementClickInterceptedException) as e:
                    ultimo_erro = e
                    logger.warning(
                        "Tentativa %s/%s falhou em %s: %s",
                        tentativa, tentativas, func.__name__, e
                    )
                    time.sleep(espera)
            raise ultimo_erro
        return wrapper
    return decorador


class NotaNaoEncontrada(Exception):
    pass


class ProdutoNaoEncontrado(Exception):
    """Código de produto não encontrado num grid (ranking de saída ou
    manutenção de estoque)."""
    pass


class ErroWtti(Exception):
    """Erro genérico de scraping (login falhou, seletor não encontrado,
    navegador crashou mesmo após tentar recuperar, etc.)"""
    pass


class WttiScraper:
    """
    Mantém UMA sessão de navegador logada e reaproveitada entre
    requisições (evitar logar de novo a cada busca, que é lento).
    Protegida por um lock porque o Selenium/WebDriver não é thread-safe:
    duas buscas concorrentes usando o mesmo driver corromperiam uma à outra.
    """

    def __init__(self):
        self._driver = None
        self._logado = False
        self._lock = threading.RLock()

    # -----------------------------------------------------------------
    # Ciclo de vida do driver
    # -----------------------------------------------------------------
    def _criar_driver(self):
        options = Options()
        if config.HEADLESS:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1366,900")
        # Evita popups nativos do Chrome que não fazem parte da página e
        # atrapalham a automação depois do login — em especial o aviso de
        # "Mude sua senha" (Leak Detection) do Gerenciador de Senhas do
        # Google, que aparece de forma assíncrona alguns segundos depois do
        # login e intercepta cliques na página por baixo dele até ser
        # fechado. "credentials_enable_service"/"password_manager_enabled"
        # sozinhos NÃO desligam esse aviso — precisa do leak_detection.
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
            "profile.default_content_setting_values.notifications": 2,
        })
        options.add_argument("--disable-notifications")
        options.add_argument(
            "--disable-features=PasswordLeakDetection,LeakDetectionUnauthenticated,PasswordChange"
        )
        driver = webdriver.Chrome(options=options)
        driver.implicitly_wait(config.IMPLICIT_WAIT_SECONDS)
        driver.set_page_load_timeout(config.EXPLICIT_WAIT_SECONDS * 2)
        return driver

    def _garantir_driver(self):
        if self._driver is None:
            logger.info("Iniciando novo navegador headless...")
            self._driver = self._criar_driver()

    def _reiniciar_driver(self):
        """Mata o navegador atual (se existir) e sobe um novo do zero.
        Usado quando o Chrome trava/crasha no meio de uma operação —
        mais comum do que se imagina em sessões headless longas."""
        logger.warning("Reiniciando o navegador do zero...")
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass  # já pode estar morto mesmo
        self._driver = None
        self._logado = False
        self._garantir_driver()

    def encerrar(self):
        with self._lock:
            if self._driver is not None:
                self._driver.quit()
                self._driver = None
                self._logado = False

    # -----------------------------------------------------------------
    # Diagnóstico — screenshot + HTML no momento do erro
    # -----------------------------------------------------------------
    def _salvar_evidencia_erro(self, rotulo):
        if self._driver is None:
            return
        try:
            os.makedirs(DEBUG_DIR, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            base = os.path.join(DEBUG_DIR, f"{timestamp}_{rotulo}")

            self._driver.save_screenshot(f"{base}.png")
            with open(f"{base}.html", "w", encoding="utf-8") as f:
                f.write(self._driver.page_source)

            logger.warning(
                "Evidência do erro salva em %s.png e %s.html — abra esses "
                "arquivos pra ver exatamente o que a tela mostrava.",
                base, base
            )
        except Exception as e:
            logger.warning("Não consegui salvar screenshot/HTML de diagnóstico: %s", e)

    # -----------------------------------------------------------------
    # Helpers de espera
    # -----------------------------------------------------------------
    def _wait(self):
        return WebDriverWait(self._driver, config.EXPLICIT_WAIT_SECONDS)

    def _esperar_visivel(self, seletor_css):
        return self._wait().until(EC.visibility_of_element_located((By.CSS_SELECTOR, seletor_css)))

    def _esperar_clicavel(self, seletor_css):
        return self._wait().until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor_css)))

    @retry_em_stale()
    def _preencher(self, seletor_css, valor):
        campo = self._esperar_visivel(seletor_css)
        campo.clear()
        campo.send_keys(valor)
        if campo.get_attribute("value") != str(valor):
            # Alguns campos (ex: o "Número" da busca, com máscara numérica
            # via JS) engolem o send_keys() do Selenium e ficam vazios.
            # Força o valor via JS e dispara os eventos que o script de
            # máscara/validação espera.
            self._driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
                "arguments[0].dispatchEvent(new Event('keyup', {bubbles:true}));",
                campo, valor,
            )

    @retry_em_stale()
    def _clicar(self, seletor_css):
        botao = self._esperar_clicavel(seletor_css)
        botao.click()

    # -----------------------------------------------------------------
    # Login
    # -----------------------------------------------------------------
    def login(self, forcar=False):
        with self._lock:
            self._garantir_driver()
            if self._logado and not forcar:
                return

            logger.info("Autenticando no WTTI...")
            try:
                self._driver.get(config.WTTI_LOGIN_URL)
                self._preencher(config.SEL_LOGIN_USERNAME, config.WTTI_USER)
                self._preencher(config.SEL_LOGIN_PASSWORD, config.WTTI_PASS)
                self._clicar(config.SEL_LOGIN_SUBMIT)
                self._esperar_visivel(config.SEL_LOGIN_SUCESSO)
            except TimeoutException:
                self._salvar_evidencia_erro("login_falhou")
                raise ErroWtti(
                    "Login no WTTI falhou ou o seletor SEL_LOGIN_SUCESSO não "
                    "corresponde a nenhum elemento pós-login. Confira credenciais "
                    "e ajuste config.py. Screenshot salvo em debug_screenshots/."
                )
            except WebDriverException as e:
                logger.warning("Navegador travou durante o login (%s). Reiniciando...", e)
                self._reiniciar_driver()
                raise ErroWtti(
                    "O navegador travou durante o login. Reiniciado — tente a "
                    "busca de novo."
                )

            self._logado = True
            logger.info("Login no WTTI concluído.")

    # -----------------------------------------------------------------
    # Busca de nota por chave de acesso ou número da NF
    # -----------------------------------------------------------------
    def buscar_nota(self, codigo):
        with self._lock:
            self._garantir_driver()
            if not self._logado:
                self.login()

            try:
                return self._buscar_nota_interno(codigo)
            except WebDriverException as e:
                logger.warning("Navegador travou durante a busca (%s). Reiniciando e tentando 1x mais...", e)
                self._salvar_evidencia_erro("navegador_travou")
                self._reiniciar_driver()
                self.login(forcar=True)
                return self._buscar_nota_interno(codigo)

    # -----------------------------------------------------------------
    # Imagens do produto (galeria da tela de Cadastro de Produtos)
    # -----------------------------------------------------------------
    def buscar_imagens_produto(self, codigo_produto):
        with self._lock:
            self._garantir_driver()
            if not self._logado:
                self.login()

            try:
                return self._buscar_imagens_produto_interno(codigo_produto)
            except WebDriverException as e:
                logger.warning("Navegador travou buscando imagens (%s). Reiniciando e tentando 1x mais...", e)
                self._salvar_evidencia_erro("navegador_travou_imagens")
                self._reiniciar_driver()
                self.login(forcar=True)
                return self._buscar_imagens_produto_interno(codigo_produto)

    def _buscar_imagens_produto_interno(self, codigo_produto):
        url = f"{config.WTTI_BASE_URL}/View/Cadastro/CadastroProduto.aspx?UID={codigo_produto}"
        logger.info("Buscando imagens do produto: %s", codigo_produto)
        self._driver.get(url)

        try:
            self._esperar_visivel(config.SEL_GALERIA_ITEM)
        except TimeoutException:
            # Produto sem nenhuma imagem cadastrada — não é um erro.
            return []

        itens_galeria = self._driver.find_elements(By.CSS_SELECTOR, config.SEL_GALERIA_ITEM)
        urls = [el.get_attribute("data-src") for el in itens_galeria]
        return [u for u in urls if u]

    # -----------------------------------------------------------------
    # Reposição — Relatório Produto x Saldo (sidebar de sugestão)
    # -----------------------------------------------------------------
    def buscar_reposicao_produto(self, codigo_produto):
        """Consulta única no Relatório Produto x Saldo: devolve descrição,
        estoque atual (sem reservas) e total de saída no mês corrente pra
        esse código. Essa tela substitui as duas usadas antes (Manutenção
        de Estoque, que dava número desatualizado, e Ranking de Produtos,
        que exigia exportar Excel por causa do ReportViewer) por uma
        consulta só, mais confiável e com histórico por NF/cliente."""
        with self._lock:
            self._garantir_driver()
            if not self._logado:
                self.login()
            try:
                return self._buscar_reposicao_produto_interno(codigo_produto)
            except WebDriverException as e:
                logger.warning("Navegador travou buscando reposição (%s). Reiniciando e tentando 1x mais...", e)
                self._salvar_evidencia_erro("navegador_travou_saldo")
                self._reiniciar_driver()
                self.login(forcar=True)
                return self._buscar_reposicao_produto_interno(codigo_produto)

    def _buscar_reposicao_produto_interno(self, codigo_produto):
        self._driver.get(config.WTTI_SALDO_URL)

        # O campo só dispara o postback no evento onchange (perde o foco),
        # não a cada tecla digitada — precisa de um Tab depois de preencher.
        self._preencher(config.SEL_SALDO_PRODUTO_INPUT, codigo_produto)
        campo = self._driver.find_element(By.CSS_SELECTOR, config.SEL_SALDO_PRODUTO_INPUT)
        campo.send_keys(Keys.TAB)

        try:
            self._esperar_visivel(config.SEL_SALDO_GRID_PRODUTOS)
        except TimeoutException:
            self._salvar_evidencia_erro(f"saldo_grid_produtos_nao_carregou_{codigo_produto}")
            raise ProdutoNaoEncontrado(
                f"Código {codigo_produto} não retornou nenhum resultado no Relatório Produto x Saldo."
            )

        linha_alvo = self._procurar_linha_produto_com_paginacao(codigo_produto)

        if linha_alvo is None:
            self._salvar_evidencia_erro(f"saldo_codigo_nao_encontrado_{codigo_produto}")
            # Códigos parecidos (ex: 571 e 1571) podem aparecer juntos no
            # grid — por isso o match é sempre por texto EXATO da coluna
            # Código, nunca "contém" ou o primeiro resultado.
            raise ProdutoNaoEncontrado(
                f"Código {codigo_produto} não encontrado entre os resultados do "
                f"Relatório Produto x Saldo (pode ter vindo só códigos parecidos)."
            )

        colunas = linha_alvo.find_elements(By.TAG_NAME, "td")
        descricao = colunas[config.COL_SALDO_DESCRICAO].text.strip()
        estoque = self._texto_para_float(colunas[config.COL_SALDO_ESTOQUE_SEM_RESERVA].text)

        botao_selecionar = linha_alvo.find_element(By.CSS_SELECTOR, "input[value='Selecionar']")
        botao_selecionar.click()

        try:
            self._esperar_visivel(config.SEL_SALDO_GRID_RESULTADO)
        except TimeoutException:
            # Produto sem nenhuma movimentação registrada — estoque ainda é
            # válido, só não tem histórico pra somar saída do mês.
            saida_mes = 0.0
        else:
            saida_mes = self._somar_saidas_do_mes()

        return {"produto": descricao, "estoque": estoque, "saida_mes": saida_mes}

    def _procurar_linha_produto_com_paginacao(self, codigo_produto):
        """O grid #gdwProdutos faz busca por "contém", não por código exato
        — buscar "45" pode trazer 1145, 1245, 145, 1457... espalhados por
        várias páginas, com "45" em si em qualquer uma delas (ou em
        nenhuma). Percorre as páginas clicando em "próxima" até achar a
        linha com o código EXATO ou esgotar a paginação."""
        MAX_PAGINAS = 20  # trava de segurança contra loop infinito
        for _ in range(MAX_PAGINAS):
            linhas = self._driver.find_elements(By.CSS_SELECTOR, f"{config.SEL_SALDO_GRID_PRODUTOS} tbody tr")
            for linha in linhas:
                if "gridviewPaginacao" in (linha.get_attribute("class") or ""):
                    continue
                colunas = linha.find_elements(By.TAG_NAME, "td")
                if len(colunas) <= config.COL_SALDO_CODIGO:
                    continue
                if colunas[config.COL_SALDO_CODIGO].text.strip() == str(codigo_produto).strip():
                    return linha

            if not self._ir_para_proxima_pagina_produtos():
                break  # não tem mais página — esgotou a busca

        return None

    def _ir_para_proxima_pagina_produtos(self):
        """Clica no link da próxima página. A paginação fica numa tabela
        SEPARADA (#tbPaginacao), fora de #gdwProdutos — não é descendente
        do grid, é uma tabela irmã na página. A linha
        <tr class="gridviewPaginacao"> tem a página atual num <span> sem
        link e as outras em <a>. Devolve True se avançou, False se já
        estava na última página ou não tinha paginação nenhuma."""
        try:
            linha_paginacao = self._driver.find_element(
                By.CSS_SELECTOR, f"{config.SEL_SALDO_PAGINACAO} tr.gridviewPaginacao"
            )
        except NoSuchElementException:
            return False  # resultado cabe numa página só, sem paginação

        celulas = linha_paginacao.find_elements(By.TAG_NAME, "td")
        pagina_atual_idx = next(
            (idx for idx, celula in enumerate(celulas) if celula.find_elements(By.TAG_NAME, "span")),
            None,
        )
        if pagina_atual_idx is None or pagina_atual_idx + 1 >= len(celulas):
            return False  # já é a última página desse bloco de paginação

        links_proxima = celulas[pagina_atual_idx + 1].find_elements(By.TAG_NAME, "a")
        if not links_proxima:
            return False

        links_proxima[0].click()
        self._esperar_visivel(config.SEL_SALDO_GRID_PRODUTOS)
        return True

    def _somar_saidas_do_mes(self):
        """Percorre a tabela de histórico (#gdwResultado) somando a coluna
        Qtd de todas as linhas com Tipo="Saídas" dentro do bloco do mês
        atual. A coluna "Mês" só vem preenchida na primeira linha de cada
        grupo de mês (fica em branco nas linhas seguintes do mesmo mês) —
        por isso guarda o último mês visto enquanto percorre. As linhas
        vêm em ordem cronológica decrescente, então dá pra parar assim que
        sair do bloco do mês alvo."""
        hoje = datetime.date.today()
        mes_alvo = f"{MESES_PT[hoje.month]} de {hoje.year}"

        linhas = self._driver.find_elements(By.CSS_SELECTOR, f"{config.SEL_SALDO_GRID_RESULTADO} tbody tr")
        mes_linha_atual = None
        dentro_do_mes_alvo = False
        total = 0.0

        for linha in linhas:
            colunas = linha.find_elements(By.TAG_NAME, "td")
            if len(colunas) <= max(config.COL_HISTORICO_MES, config.COL_HISTORICO_TIPO, config.COL_HISTORICO_QTD):
                continue

            texto_mes = colunas[config.COL_HISTORICO_MES].text.strip()
            if texto_mes:
                if dentro_do_mes_alvo and texto_mes != mes_alvo:
                    break  # saiu do bloco do mês alvo, não precisa olhar o resto
                mes_linha_atual = texto_mes
                dentro_do_mes_alvo = (mes_linha_atual == mes_alvo)

            if mes_linha_atual != mes_alvo:
                continue

            tipo = colunas[config.COL_HISTORICO_TIPO].text.strip()
            if tipo != "Saídas":
                continue  # "Reservas"/"Entradas" não contam como saída

            total += self._texto_para_float(colunas[config.COL_HISTORICO_QTD].text)

        return total

    @staticmethod
    def _texto_para_float(texto):
        texto = (texto or "").strip()
        if not texto:
            return 0.0
        try:
            return float(texto.replace(".", "").replace(",", "."))
        except ValueError:
            return 0.0

    def _selecionar_nota_por_tipo(self, codigo, tipo_desejado):
        """
        A busca leva a um grid de resultados (gdwNotas) que pode listar mais
        de um documento pro mesmo número (ex: NF-e de saída e o CT-e do
        frete). Precisamos achar a linha cujo texto de "Tipo" bate com
        tipo_desejado e clicar no botão "Selecionar" dessa linha específica
        pra abrir a tela com os itens (gdwProduto).
        """
        try:
            self._esperar_visivel(config.SEL_TABELA_NOTAS)
        except TimeoutException:
            # Pode não existir grid de resultados (ex: já foi direto pra
            # tela de itens) — deixa o fluxo seguir normalmente.
            return

        linhas = self._driver.find_elements(By.CSS_SELECTOR, f"{config.SEL_TABELA_NOTAS} tbody tr")
        linha_alvo = None
        for linha in linhas:
            celulas = linha.find_elements(By.TAG_NAME, "td")
            if any(c.text.strip() == tipo_desejado for c in celulas):
                linha_alvo = linha
                break

        if linha_alvo is None:
            self._salvar_evidencia_erro(f"tipo_nao_encontrado_{codigo}")
            raise NotaNaoEncontrada(
                f"O código {codigo} retornou resultados, mas nenhum do tipo "
                f'"{tipo_desejado}".'
            )

        botao_selecionar = linha_alvo.find_element(
            By.CSS_SELECTOR, "a[id*='btnSelecionar'], input[id*='btnSelecionar'], input[value='Selecionar']"
        )
        botao_selecionar.click()

    @retry_em_stale()
    def _garantir_tipo_documento(self):
        """
        "Tipo de Documento" é um dropdown customizado de checkboxes (não um
        <select>). Mesmo quando o checkbox certo já vem marcado no HTML
        renderizado pelo servidor, a legenda do widget continua mostrando
        "Selecione" e a busca retorna zero linhas — o filtro só é aplicado
        de verdade quando o clique acontece (o widget sincroniza seu estado
        via JS no evento de clique, não a partir do atributo checked cru).
        Por isso desmarcamos e remarcamos quando já estava marcado, só pra
        garantir que o clique (e o evento) aconteça de qualquer forma.
        """
        toggle = self._esperar_clicavel(config.SEL_TIPO_DOC_DROPDOWN)
        toggle.click()
        checkbox = self._esperar_visivel(config.SEL_TIPO_DOC_CHECKBOX)
        if checkbox.is_selected():
            checkbox.click()
        checkbox.click()
        toggle.click()  # fecha o dropdown

    def _buscar_nota_interno(self, codigo):
        logger.info("Buscando nota: %s", codigo)
        self._driver.get(config.WTTI_SEARCH_URL)
        self._garantir_tipo_documento()

        try:
            self._preencher(config.SEL_BUSCA_INPUT, codigo)
            self._clicar(config.SEL_BUSCA_SUBMIT)
        except TimeoutException:
            # Sessão pode ter expirado no meio do caminho — tenta logar de novo, uma vez
            logger.warning("Timeout na busca. Tentando novo login e nova tentativa.")
            self.login(forcar=True)
            self._driver.get(config.WTTI_SEARCH_URL)
            self._preencher(config.SEL_BUSCA_INPUT, codigo)
            self._clicar(config.SEL_BUSCA_SUBMIT)

        self._selecionar_nota_por_tipo(codigo, config.TIPO_NOTA_DESEJADO)

        if config.SEL_RESULTADO_IFRAME:
            self._wait().until(
                EC.frame_to_be_available_and_switch_to_it((By.CSS_SELECTOR, config.SEL_RESULTADO_IFRAME))
            )

        try:
            self._esperar_visivel(config.SEL_TABELA_ITENS)
        except TimeoutException:
            self._salvar_evidencia_erro(f"nota_nao_encontrada_{codigo}")
            if config.SEL_RESULTADO_IFRAME:
                self._driver.switch_to.default_content()
            raise NotaNaoEncontrada(f"Nenhuma nota encontrada para o código {codigo}")

        cliente = self._texto_seguro(config.SEL_CLIENTE_NOME)
        numero_nf = self._texto_seguro(config.SEL_NUMERO_NF)

        linhas = self._driver.find_elements(By.CSS_SELECTOR, config.SEL_LINHAS_ITENS)
        itens = []
        for linha in linhas:
            colunas = linha.find_elements(By.TAG_NAME, "td")
            # A linha de cabeçalho do gdwProduto usa <th>, não <td>, então
            # colunas fica vazia pra ela e cai fora aqui naturalmente.
            if len(colunas) <= max(config.COL_CODIGO, config.COL_PRODUTO, config.COL_QTD):
                continue
            try:
                itens.append({
                    "codigo": colunas[config.COL_CODIGO].text.strip(),
                    "produto": colunas[config.COL_PRODUTO].text.strip(),
                    "qtd": float(colunas[config.COL_QTD].text.strip().replace(",", ".")),
                    "unidade": "UN",  # gdwProduto não tem coluna de unidade
                })
            except ValueError:
                logger.warning("Linha com quantidade não numérica ignorada: %s", linha.text)

        if config.SEL_RESULTADO_IFRAME:
            self._driver.switch_to.default_content()

        if not itens:
            self._salvar_evidencia_erro(f"sem_itens_{codigo}")
            raise NotaNaoEncontrada(f"Nota {codigo} encontrada, mas sem itens no grid.")

        return {
            "chave": codigo if len(codigo) == 44 else "",
            "nNF": numero_nf or (codigo if len(codigo) != 44 else ""),
            "cliente": cliente or "Cliente não identificado",
            "itens": itens,
        }

    def _texto_seguro(self, seletor_css):
        try:
            elemento = self._driver.find_element(By.CSS_SELECTOR, seletor_css)
        except NoSuchElementException:
            return ""
        texto = elemento.text.strip()
        if not texto and elemento.tag_name.lower() in ("input", "textarea"):
            # <input>/<textarea> não expõem o conteúdo via .text no Selenium
            # (readonly ou não) — o valor real está no atributo "value".
            texto = (elemento.get_attribute("value") or "").strip()
        return texto


# Instância única reaproveitada por todas as requisições da API
scraper = WttiScraper()


def buscar_nota(codigo):
    """Função de conveniência — é isso que o app.py importa e chama."""
    return scraper.buscar_nota(codigo)


def buscar_imagens_produto(codigo_produto):
    """Função de conveniência — é isso que o app.py importa e chama."""
    return scraper.buscar_imagens_produto(codigo_produto)


def buscar_reposicao_produto(codigo_produto):
    """Função de conveniência — é isso que o app.py importa e chama."""
    return scraper.buscar_reposicao_produto(codigo_produto)
