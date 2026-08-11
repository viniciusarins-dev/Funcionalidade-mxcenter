# API de Conferência de Pedidos — Integração com WTTI (mxcenter)

API em Flask que faz login no sistema **WTTI** (`mxcenter.wtti.app`) via
**Selenium**, busca uma nota pelo número curto da NF ou pela chave de acesso
completa, e devolve os itens em JSON — pronta pra alimentar uma tela de
conferência/bancada (`static/index.html`, servida em `/`).

## Por que Selenium em vez de uma API oficial?

O WTTI não expõe uma API pública, então a automação de tela (Selenium) é o
único jeito de buscar a nota por lá. Uma alternativa que chegou a ser
avaliada foi consultar a SEFAZ diretamente (webservice `NFeDistribuicaoDFe`,
usando o certificado digital da empresa) — mas essa via não serve pro caso de
uso principal (notas de **venda**, onde a empresa é a **emitente**): a SEFAZ
bloqueia justamente o emitente de reconsultar o próprio XML por esse
webservice (regra H17 da NT2014.002). Por isso o projeto seguiu com o
caminho WTTI/Selenium, que é o que está implementado hoje.

## 1. Pré-requisitos

- Python 3.10+
- **Google Chrome instalado** na máquina que vai rodar a API — o Selenium
  4.27 usa o "Selenium Manager" pra baixar automaticamente o `chromedriver`
  compatível, mas o **Chrome em si** precisa já estar instalado.

## 2. Instalação

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configuração

```bash
cp .env.example .env
```

Preencha no `.env`, no mínimo:

- `WTTI_USER` / `WTTI_PASS` — credenciais de login no WTTI.
- `WTTI_BASE_URL`, `WTTI_LOGIN_URL`, `WTTI_SEARCH_URL` — já vêm com valores
  padrão apontando pro `mxcenter.wtti.app`.

Os `SEL_*` (seletores CSS de cada campo/botão da tela) já vêm preenchidos com
os valores descobertos e testados nesse ambiente — veja `GUIA_SELETORES.md`
se precisar reajustar algum (ex: depois de uma atualização do WTTI que mude
o HTML da tela).

**O `.env` nunca deve ir pro Git** (tem a senha do WTTI). O `.gitignore` já
está configurado pra isso.

## 4. Testando login e busca antes de rodar a API

Com `HEADLESS=false` no `.env` (assim o Chrome abre visível e dá pra ver
onde trava, se travar):

```bash
python testar_login.py
python testar_busca.py <numero_ou_chave_da_nota>
```

Se algum passo falhar, screenshots + HTML da página no momento do erro são
salvos em `debug_screenshots/` (pasta ignorada pelo Git — pode conter nome
de cliente e itens de pedido).

## 5. Rodando localmente

```bash
python3 app.py
```

- `http://localhost:5000/` → a tela de conferência.
- `http://localhost:5000/api/...` → a API.

### Acessando pelo celular (mesma rede Wi-Fi)

1. Descubra o IP local da máquina (`ipconfig` no Windows, `ifconfig`/`ip a`
   no Mac/Linux).
2. Libere a porta no firewall se for pedido.
3. No celular, na mesma rede Wi-Fi, acesse `http://SEU-IP-LOCAL:5000/`.
4. Teste primeiro `http://SEU-IP-LOCAL:5000/api/health`.

## 6. Hospedando na nuvem

Diferente de uma API puramente HTTP, esse projeto **depende de um navegador
Chrome real rodando no servidor** (Selenium). Isso muda o requisito de
hospedagem:

- **Não funciona** num runtime "Python" genérico tipo o plano free padrão do
  Render, porque essas imagens não têm o Google Chrome instalado.
- Pra hospedar de verdade, é preciso um serviço que rode um **Dockerfile**
  próprio instalando o Google Chrome (ou uma imagem base que já inclua
  Chrome + chromedriver), e então rodar o `Procfile`/`gunicorn` normalmente
  dentro desse container.
- Esse Dockerfile ainda não existe neste projeto — é um passo pendente antes
  de qualquer deploy em nuvem. Até lá, o uso é local ou em rede interna.

## 7. Endpoints da API

- `GET /api/health` — verificação simples de que a API está no ar.
- `GET /api/notas/<codigo>` — busca a nota pelo número curto **ou** pela
  chave de acesso completa (44 dígitos). Retorna:
  ```json
  {
    "chave": "35240112345678000199550010000012341123456789",
    "nNF": "1234",
    "cliente": "Nome do Cliente",
    "itens": [
      { "codigo": "1552", "produto": "Nome do produto", "qtd": 10, "unidade": "UN" }
    ]
  }
  ```
  - `400` se o código enviado for vazio.
  - `404` se nenhuma nota for encontrada pra esse código.
  - `502` se der erro de login/scraping no WTTI.
  - `500` em erro interno inesperado.
- `GET /api/produtos/<codigo>/imagens` — lista de URLs de imagens do produto
  (galeria da tela de Cadastro de Produtos). Retorna
  `{ "codigo": "1552", "imagens": ["https://mxcenter.wtti.app/Site/000182.jpg"] }`.
- `GET /api/produtos/<codigo>/reposicao` — descrição, estoque atual, e
  médias mensais de saída (vendas) e compra desde 01/01 do ano atual
  (Relatório Produto x Saldo), usado pela sidebar de sugestão de pedido
  da tela. Retorna:
  ```json
  {
    "codigo": "1552",
    "produto": "Nome do produto",
    "saida_media_mensal": 106.0,
    "compra_media_mensal": 40.0,
    "estoque_sistema": 20.0
  }
  ```
  O cálculo da quantidade sugerida (e a comparação com o estoque contado à
  mão, pra achar "furos") acontece no front-end, não aqui — veja a seção 9.
- `POST /api/login` — força um novo login no WTTI (útil se a sessão expirar
  no meio do dia).

Todas as rotas de API respeitam `API_KEY`: se configurada no `.env`, exigem o
header `X-API-Key` em toda requisição (retorna `401` sem ele).

## 8. Conectando o front-end à API

A tela é servida pelo mesmo Flask (`static/index.html`), então
`window.location.origin` já resolve a URL da API automaticamente — funciona
tanto em `http://localhost:5000` quanto em `http://SEU-IP-LOCAL:5000`, sem
editar nada.

Se ativar `API_KEY` no `.env`, edite o `fetch()` da tela pra enviar o header
`X-API-Key` com a mesma chave.

## 9. Sidebar de sugestão de reposição

Botão "📦 Reposição" no canto superior direito da tela abre um painel onde
dá pra digitar o código de um produto. O fluxo é proposital:

1. Digita o código e busca — a API consulta o **Relatório Produto x
   Saldo** do WTTI desde 01/01 do ano atual até hoje (traz estoque em
   tempo real + histórico de saída/compra por mês/NF/cliente numa tela
   só).
2. Antes de mostrar qualquer número do sistema, a tela **pergunta**:
   "Quantos você tem realmente em estoque?" — o operador digita a
   contagem física, sem ver o número do sistema antes, pra não vender a
   resposta.
3. Só depois de confirmar é que aparecem:
   - **Saída média/mês** — total de saídas (`Tipo = Saídas`) desde 01/01
     dividido pelo número do mês atual (ex: agosto = ÷8).
   - **Compra média/mês** — mesma conta, pras linhas `Tipo = Entradas`.
   - **Estoque no sistema** — pra comparar com o que foi contado.
   - **Furo** — diferença entre estoque do sistema e o contado, sinalizada
     em cores.
   - **Meses de cobertura** (editável, padrão 2) e a **sugestão de
     pedido**: `saída média/mês × meses de cobertura − estoque contado`.

Os seletores do Relatório Produto x Saldo (`SEL_SALDO_*`) foram
confirmados por inspeção do HTML real e validados de ponta a ponta com
`testar_reposicao.py` — é um grid comum, sem a complicação de classes
CSS dinâmicas que o Ranking de Produtos (tela usada antes, já
substituída) tinha por usar o controle Microsoft ReportViewer. Veja
`GUIA_SELETORES.md` (Passo 7) pros detalhes.

## 10. Limitações importantes

- **Depende do layout do WTTI.** Se a tela mudar (atualização do sistema),
  os seletores em `.env` (`SEL_*`) podem parar de bater — veja
  `GUIA_SELETORES.md` pra reajustar.
- **Uma sessão de navegador compartilhada.** O `scraper.py` mantém uma única
  instância de Chrome logada, reaproveitada entre requisições, protegida por
  lock (thread-safe). Isso só funciona corretamente com **1 worker** do
  Gunicorn — não aumente `--workers` sem repensar essa arquitetura, ou vai
  subir múltiplas sessões Chrome simultâneas no WTTI.
- **`debug_screenshots/` pode conter dados de cliente/pedido.** Já está no
  `.gitignore`; não remova essa exclusão.
- **Sem API pública oficial.** Diferente de uma consulta direta à SEFAZ,
  qualquer instabilidade do WTTI (timeout, manutenção, mudança de tela)
  afeta diretamente a API.

## 11. Estrutura dos arquivos

```
├── app.py                    # rotas Flask (API + serve a tela em /)
├── scraper.py                 # automação Selenium do WTTI (login, busca de nota, imagens, reposição)
├── config.py                  # todas as configurações via variáveis de ambiente
├── testar_login.py            # teste isolado de login no WTTI
├── testar_busca.py            # teste isolado de busca de nota no WTTI
├── testar_reposicao.py        # teste isolado de estoque + médias mensais de saída/compra (sidebar de reposição)
├── static/
│   └── index.html             # a tela de conferência (bancada), servida em "/"
├── GUIA_SELETORES.md          # passo a passo pra achar/reajustar os seletores CSS do WTTI
├── Procfile                   # comando de start (gunicorn)
├── .gitignore                 # garante que .env, *.pfx e debug_screenshots/ nunca vão pro Git
├── requirements.txt
├── .env / .env.example
└── README.md
```
