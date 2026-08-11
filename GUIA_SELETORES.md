# Guia — Encontrando os seletores certos do WTTI

> **Status (2026-08-11):** login, busca de nota (Passos 1-6) e a sidebar
> de reposição via Relatório Produto x Saldo (Passo 7) validados de
> ponta a ponta contra o WTTI real, incluindo paginação. O Estoque
> Mínimo (também Passo 7, lido de `CadastroProduto.aspx`) foi só testado
> isoladamente com dados simulados — ainda não rodou contra o WTTI de
> verdade. Este guia continua valendo como referência pra quando o WTTI
> mudar de layout no futuro e algum seletor parar de bater.

Siga esses passos na ordem. Cada um leva 2-5 minutos. Não precisa saber
programar — é só inspecionar a página e copiar um texto.

---

## Passo 0 — Confira o screenshot de ontem primeiro

Abra `debug_screenshots\..._login_falhou.png` (o mais recente). Isso já
adianta se o problema é seletor errado (a tela mostra o login normal do
WTTI) ou outra coisa (fora do ar, senha errada, CAPTCHA, manutenção).

Se a tela mostrar o login normal do WTTI → siga para o Passo 1.
Se mostrar erro/manutenção/página diferente → me manda uma descrição ou
print antes de continuar, o problema pode não ser de seletor.

---

## Passo 1 — Abrir o WTTI manualmente e logar

1. Abra o Chrome normal (não o do teste).
2. Acesse a URL de login do WTTI (a mesma do `.env`, `WTTI_LOGIN_URL`).
3. **Antes de fazer login**, aperte `F12` para abrir o DevTools.
4. Clique na aba **Elements** (ou "Elementos") do DevTools.

---

## Passo 2 — Achar o seletor do campo de USUÁRIO

1. Na tela de login (ainda deslogado), clique com o **botão direito**
   em cima do campo onde você digita o usuário/login.
2. Clique em **Inspecionar** (Inspect).
3. O DevTools vai abrir com aquela linha de HTML já destacada, tipo:
   ```html
   <input type="text" id="txtUsuario" name="ctl00$..." ... >
   ```
4. Copie o valor do atributo **id** (a parte entre aspas depois de `id=`).
5. Anote na tabela lá embaixo, na linha `SEL_LOGIN_USERNAME`, **com um `#`
   na frente** (ex: se o id for `campoLogin`, anote `#campoLogin`).

Repita o mesmo processo para:
- **Campo de senha** → `SEL_LOGIN_PASSWORD`
- **Botão de entrar/login** → `SEL_LOGIN_SUBMIT`

---

## Passo 3 — Achar o seletor de "login deu certo"

Esse é o mais importante e o que provavelmente está errado agora.

1. Faça login de verdade, manualmente, no WTTI (usuário e senha reais).
2. Assim que a tela carregar (já logado, mostrando o menu/dashboard),
   aperte `F12` de novo.
3. Clique com o botão direito em **qualquer elemento que só aparece
   depois de logado** — pode ser o nome do usuário no canto, um item de
   menu, o logo, qualquer coisa que with certeza não aparece na tela de
   login.
4. Clique em **Inspecionar**, copie o `id` desse elemento (mesmo jeito
   do Passo 2).
5. Anote em `SEL_LOGIN_SUCESSO` (com `#` na frente).

**Se esse elemento não tiver `id`** (alguns sistemas antigos não usam
id em tudo), me avisa — tem outras formas de selecionar (por classe CSS
ou texto), só precisa ajustar o código.

---

## Passo 4 — Achar os seletores da tela de CONSULTA DE NOTA

Ainda logado, vá até a tela onde você digita o número da nota e vê o
resultado (a mesma tela que o operador vai usar).

Repita o processo de inspecionar (botão direito → Inspecionar → copiar
`id`) para:

| O que inspecionar | Variável no .env |
|---|---|
| Campo onde digita o número da NF | `SEL_BUSCA_INPUT` |
| Botão de buscar/consultar | `SEL_BUSCA_SUBMIT` |
| Nome do cliente no resultado | `SEL_CLIENTE_NOME` |
| Número da NF no resultado | `SEL_NUMERO_NF` |
| A tabela/grid inteira de itens | `SEL_TABELA_ITENS` |

**Para `SEL_LINHAS_ITENS`:** inspecione uma **linha** da tabela de itens
(uma linha de produto), veja se a tabela tem `<tbody>` dentro dela. Se
o id da tabela for, por exemplo, `gridItens`, o valor geralmente é:
```
#gridItens tbody tr
```

**Para `COL_PRODUTO`, `COL_QTD`, `COL_UNIDADE`:** conte as colunas da
tabela da esquerda pra direita, começando do **0**. Ex: se a 1ª coluna é
um checkbox, a 2ª é o nome do produto, a 3ª é quantidade, a 4ª é
unidade → `COL_PRODUTO=1`, `COL_QTD=2`, `COL_UNIDADE=3`.

---

## Passo 5 — Se a tela de resultado ficar dentro de um "quadro" separado (iframe)

Alguns sistemas antigos carregam o resultado da busca dentro de um
`<iframe>`. Pra saber se é o caso: no DevTools, quando você inspeciona
o campo de resultado, veja se logo acima dele, na árvore de elementos,
aparece uma tag `<iframe ...>` envolvendo tudo.

- Se **sim**: inspecione o próprio `<iframe>`, copie o id, e coloque em
  `SEL_RESULTADO_IFRAME`.
- Se **não**: deixe `SEL_RESULTADO_IFRAME` vazio (já está assim).

---

## Tabela para preencher enquanto investiga

Preencha aqui (ou direto no `.env`) conforme for achando:

```
SEL_LOGIN_USERNAME=           # já preenchido: #txtUsuario
SEL_LOGIN_PASSWORD=           # já preenchido: #txtSenha
SEL_LOGIN_SUBMIT=             # já preenchido: #btnAcessar
SEL_LOGIN_SUCESSO=            # já preenchido: #lblTelefone

SEL_BUSCA_INPUT=              # já preenchido: #ctl00_ContentPlaceHolder1_pesquisaApplet_ctl03_txtValor
SEL_BUSCA_SUBMIT=             # já preenchido: #btnConsultar
SEL_RESULTADO_IFRAME=
SEL_CLIENTE_NOME=             # já preenchido: #txtRazaoSocial
SEL_NUMERO_NF=                # já preenchido: #txtNF
SEL_TABELA_ITENS=             # já preenchido: #gdwProduto
SEL_LINHAS_ITENS=             # já preenchido: #gdwProduto tbody tr
COL_PRODUTO=                  # já preenchido: 1
COL_QTD=                      # já preenchido: 2
```

O grid de itens (`gdwProduto`) não tem coluna de unidade — o scraper já usa
"UN" fixo pra todo item, então não existe mais `COL_UNIDADE`.

---

## Passo 4.1 — A busca abre um grid de resultados primeiro (já tratado e testado)

Descobrimos que a busca não leva direto pros itens: primeiro aparece um
grid de resultados (`gdwNotas`), que pode listar mais de um documento pro
mesmo número (ex: a NF-e de saída e o CT-e do frete junto). O scraper agora:

1. Espera o grid `#gdwNotas` aparecer.
2. Acha a linha cuja coluna "Tipo" tem o texto exato configurado em
   `TIPO_NOTA_DESEJADO` (padrão: `Nota Fiscal Eletrônica de Saída`).
3. Clica no botão "Selecionar" dessa linha (`<a id="btnSelecionar">`) — só
   então o grid de itens (`#gdwProduto`) aparece.

Testado de ponta a ponta com `python testar_busca.py 3944` em
2026-08-10 e funcionou (login → busca → seleção da linha certa → itens).

Se um dia o grid de resultados tiver outro texto de "Tipo" (ex: se a
empresa também usar essa tela pra NF-e de entrada), ajuste
`TIPO_NOTA_DESEJADO` no `.env`.

**Duas pegadinhas que causaram bastante dor de cabeça e já estão
corrigidas no `scraper.py`, mas fica registrado caso o problema volte:**

- O campo "Número" da busca tem uma máscara numérica via JS que engole o
  `send_keys()` do Selenium (o campo fica vazio mesmo "digitando" certo).
  O `_preencher()` agora detecta isso e força o valor via JavaScript como
  fallback.
- Pouco depois do login, o Chrome pode mostrar o aviso nativo "Mude sua
  senha" (Google Password Manager / Leak Detection) por cima da página,
  interceptando cliques nos campos por baixo dele de forma imprevisível.
  Isso é desligado via `prefs` no `_criar_driver()`
  (`profile.password_manager_leak_detection` etc.) — se um dia esse popup
  voltar a aparecer (ex: depois de trocar a senha do WTTI), é o primeiro
  lugar pra olhar.

Na tela que abre depois de clicar Selecionar, o nome do cliente e o
número da NF ficam em campos `<input readonly>` (`#txtRazaoSocial` e
`#txtNF`), não em `<label>`. Por isso o `scraper.py` lê o atributo
`value` desses campos, e não o texto visível — um `<input>` sempre
retorna texto vazio no Selenium, mesmo com conteúdo preenchido.

Todos os seletores, tanto da tela de LOGIN quanto da tela de CONSULTA,
já estão confirmados (ver nota de status no topo deste arquivo).

---

## Passo 6 — Testar de novo

Depois de preencher o `.env` com os valores reais, no terminal (com o
`venv` ativado, na pasta certa):

```powershell
python testar_login.py
python testar_busca.py <numero_da_nota>
```

Se aparecer `✅ LOGIN FUNCIONOU!` e depois `✅ BUSCA FUNCIONOU!`, os
seletores estão certos (é exatamente o que aconteceu em 2026-08-11 com
os valores default atuais).

---

## Passo 7 — Seletores da sidebar de reposição (Relatório Produto x Saldo)

> **Histórico:** as duas primeiras tentativas pra essa sidebar foram
> descartadas: a tela de Manutenção de Estoque (dado desatualizado) e o
> Ranking de Produtos (ReportViewer com classes CSS dinâmicas, exigia
> exportar Excel). O **Relatório Produto x Saldo** resolve as duas coisas
> numa tela só — estoque em tempo real e histórico de saída por
> mês/NF/cliente — e é um grid HTML comum, sem a complicação do
> ReportViewer.

URL: `https://mxcenter.wtti.app/View/Relatorio/RelatorioProdutoSaldo.aspx`

### Como funciona

1. Preenche **Data Inicial** (`#txtDataI`) com `01/01/<ano atual>` e
   **Data Final** (`#txtDataF`) com a data de hoje — a tela sozinha só
   carrega os últimos 3 meses por padrão, então isso é necessário pra
   calcular médias desde o início do ano.
2. Digita o código no campo **Produto** (`#txtCodProduto`) e sai do campo
   (o campo só dispara a busca no evento `onchange`, que só acontece
   quando perde o foco — por isso o scraper manda um Tab depois de
   preencher, não basta digitar). Esse postback envia o formulário
   inteiro, incluindo as datas preenchidas no passo 1.
3. Isso preenche o grid `#gdwProdutos` com os produtos cujo código bate
   (pode vir mais de um parecido, ex: `571` e `1571` juntos — o scraper
   sempre confere o texto **exato** da coluna Código, nunca pega a
   primeira linha).
4. Nesse mesmo grid já vem a coluna **"Estoque s/ Reservas"** — esse é o
   estoque atual usado pela sidebar, direto dali, sem precisar de mais
   nenhum clique.
5. Clicar em **Selecionar** na linha certa carrega a tabela de histórico
   `#gdwResultado` (Mês/Dia/NF/Tipo/Interessado/Saldo/Qtd/...), já
   filtrada desde 01/01 — o scraper soma a coluna `Qtd` de todas as
   linhas com `Tipo = Saídas` (vendas) e, separadamente, `Tipo = Entradas`
   (compras), e divide cada soma pelo número do mês atual (ex: agosto =
   8) pra chegar numa média mensal de cada um. `Reservas` não entra em
   nenhuma das duas.
6. Depois disso, o scraper navega pra `View/Cadastro/CadastroProduto.aspx?UID=<codigo>`
   (a mesma tela já usada pra buscar fotos de produto) e lê o **Estoque
   Mínimo** cadastrado, no painel `#pnlDetalhesProduto` — usado como piso
   de segurança na sidebar, com margem editável (ver seção 9 do README).

### Pegadinha da paginação do `#gdwProdutos` ✅ (corrigida em 2026-08-11)

A busca no campo Produto é por "**contém**", não por código exato — o
código `#gdwProdutos` faz uma busca ampla: buscar `"45"` traz `1145`,
`1245`, `145`, `1457`... espalhados por várias páginas, e o código exato
`"45"` pode estar em qualquer uma delas (ou em nenhuma). Testado com o
código real `41` — existia, mas estava na página 2.

**Erro que já aconteceu:** a linha de paginação (`<tr
class="gridviewPaginacao">`) fica numa **tabela separada** —
`#tbPaginacao` — que **não é descendente** de `#gdwProdutos`, é uma
tabela irmã em outro lugar da página (confirmado inspecionando o
breadcrumb do DevTools). A primeira versão do código procurava a
paginação DENTRO de `#gdwProdutos` (`#gdwProdutos tr.gridviewPaginacao`),
nunca achava nada, e desistia sempre na primeira página — mesmo quando
o produto existia numa página seguinte. Corrigido usando
`SEL_SALDO_PAGINACAO=#tbPaginacao` como seletor independente.

O scraper agora percorre as páginas clicando no link da próxima
(`_ir_para_proxima_pagina_produtos`) até achar o código exato ou
esgotar a paginação (limite de segurança: 20 páginas).

### Seletores confirmados (por inspeção do HTML real em 2026-08-11)

```
SEL_SALDO_DATA_INICIAL=#txtDataI
SEL_SALDO_DATA_FINAL=#txtDataF
SEL_SALDO_PRODUTO_INPUT=#txtCodProduto
SEL_SALDO_GRID_PRODUTOS=#gdwProdutos
SEL_SALDO_PAGINACAO=#tbPaginacao
COL_SALDO_CODIGO=0
COL_SALDO_DESCRICAO=1
COL_SALDO_ESTOQUE_SEM_RESERVA=4
SEL_SALDO_GRID_RESULTADO=#gdwResultado
COL_HISTORICO_TIPO=3
COL_HISTORICO_QTD=6
SEL_ESTOQUE_MINIMO=#lblEstoqueProdutoMin
```

A lógica de soma por tipo foi testada com os dados reais que apareceram
na tela pro produto 571 (BATENTE 14MM - CRF250F): 6 linhas "Saídas" em
Agosto/2026 (5+8+2+6+2+2 = 25) e 1 linha "Reservas" (corretamente
ignorada) — bate certinho com o algoritmo implementado. Como agora soma
o ANO INTEIRO (não só um bloco de mês), não precisa mais rastrear a
coluna Mês nem parar de escanear no meio da tabela — só soma tudo que
for `Tipo = Saídas` ou `Tipo = Entradas` na tabela inteira e divide pelo
número do mês atual.

### Testar

```powershell
python testar_reposicao.py <codigo_de_um_produto_que_voce_sabe_o_estoque_e_a_saida>
```

**Validado de ponta a ponta em 2026-08-11** contra o WTTI real: código
`571` (BATENTE 14MM - CRF250F, estoque 136) e código `139` funcionaram
direto na primeira página. Códigos curtos que precisam de paginação
(`41`, `45`) só passaram a funcionar depois da correção do
`SEL_SALDO_PAGINACAO` acima. Depois disso, mudamos de "saída do mês
corrente" pra "média mensal desde 01/01" — os números de saída
reportados nos testes anteriores (25 unidades pro 571, por exemplo) se
referem à versão antiga (só o mês); não comparáveis diretamente com a
média atual.

---

## Se continuar dando `❌` nos testes de login/busca (Passos 1-6), me manda:
1. O novo screenshot de `debug_screenshots\`.
2. O `id` que você achou pra `SEL_LOGIN_SUCESSO` — às vezes o elemento
   certo demora um pouco a aparecer na tela (precisa de mais tempo de
   espera), ou o id muda dinamicamente a cada carregamento (nesse caso,
   me avisa que ajustamos a estratégia).
