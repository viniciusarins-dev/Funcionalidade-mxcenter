# Guia — Encontrando os seletores certos do WTTI

> **Status (2026-08-11):** login e busca de nota (Passos 1-6 abaixo) já
> estão validados de ponta a ponta — `testar_login.py` e
> `testar_busca.py 3944` rodaram com sucesso usando os valores que já vêm
> como default em `config.py`/`.env.example`. **Pendente:** os seletores
> da sidebar de reposição (saída do mês + estoque, Passo 7) ainda não
> foram inspecionados no HTML real — são só um palpite. Este guia
> continua valendo como referência pra quando o WTTI mudar de layout no
> futuro e algum seletor parar de bater.

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

## Passo 7 — Seletores da sidebar de reposição (saída do mês + estoque)

Diferente dos passos anteriores, essas duas telas **ainda não foram
inspecionadas** — os valores em `.env.example`/`config.py` são só um
palpite razoável baseado no padrão do resto do sistema (grids `gdwXxx`).
É bem provável que precisem de ajuste na primeira rodada.

### 7.1 — Relatório de Ranking de Produtos (saída do mês)

URL: `https://mxcenter.wtti.app/View/Relatorio/RelatorioRankingProdutos.aspx`

1. Acesse a tela logado e repare: ela já carrega o mês atual sozinha, ou
   precisa selecionar um mês/período antes de mostrar a lista?
   - Se **já carrega sozinha**: deixe `SEL_RANKING_MES_INPUT` e
     `SEL_RANKING_SUBMIT` vazios no `.env` (o scraper pula essa etapa).
   - Se **precisa selecionar um período**: inspecione (botão direito →
     Inspecionar) o campo de mês/data e o botão de aplicar filtro, anote
     os `id`s em `SEL_RANKING_MES_INPUT` e `SEL_RANKING_SUBMIT`. Me avisa
     também qual é o formato esperado (ex: `08/2026`, `2026-08`, um
     dropdown de mês + outro de ano) — o `scraper.py` precisa saber pra
     preencher certo (hoje ele tenta preencher com string vazia, que
     provavelmente vai precisar virar código específico depois que você
     descrever o campo).
2. Inspecione a **tabela de resultados** (a lista de produtos com
   quantidade vendida). Anote o `id` dela em `SEL_RANKING_TABELA`, e o
   seletor de linha (geralmente `#idDaTabela tbody tr`) em
   `SEL_RANKING_LINHAS`.
3. Conte as colunas da tabela da esquerda pra direita (começando do 0) e
   anote em `.env`:
   - `COL_RANKING_CODIGO` — coluna com o código do produto.
   - `COL_RANKING_QTD` — coluna com a quantidade vendida/saída no período.

### 7.2 — Manutenção de Estoque por Filial ✅ (validado em 2026-08-11)

URL: `https://mxcenter.wtti.app/View/Cadastro/ManutencaoEstoqueFilial.aspx`

Seletores confirmados com `testar_reposicao.py 203` (produto "BATENTE
16MM - SHOWA", estoque = 53):

```
SEL_ESTOQUE_BUSCA_INPUT=#txtCodProduto
SEL_ESTOQUE_BUSCA_SUBMIT=#btnPesquisa
SEL_ESTOQUE_TABELA=#gdwVendas
SEL_ESTOQUE_LINHAS=#gdwVendas tbody tr
COL_ESTOQUE_QTD=2
```

`COL_ESTOQUE_CODIGO` ficou no default (`0`) — não foi confirmado
explicitamente qual coluna do grid `#gdwVendas` tem o código do produto.
Se algum produto vier com estoque `0` errado (o código pode não estar
batendo na coluna certa), esse é o primeiro lugar pra conferir.

### 7.3 — Testar

```powershell
python testar_reposicao.py <codigo_de_um_produto_que_voce_sabe_a_saida_e_o_estoque>
```

Compare os dois números impressos (`Saída do mês` e `Estoque no sistema`)
com o que você vê manualmente nas telas do WTTI pra esse mesmo produto.
Se baterem, os seletores estão certos. Se vierem `0` (ou errados), confira
`debug_screenshots/` — o script salva screenshot em caso de erro — e
ajusta os `SEL_RANKING_*`/`SEL_ESTOQUE_*` no `.env`.

**Lembrete:** o estoque desse relatório é sabidamente desatualizado em
relação à contagem física real (você já mencionou isso) — não é o
scraper que está errado se o número bater com o que o *sistema* mostra
mas não com o que tem na prateleira. É exatamente pra isso que a sidebar
deixa digitar o estoque contado à mão, pra comparar.

---

## Se continuar dando `❌` nos testes de login/busca (Passos 1-6), me manda:
1. O novo screenshot de `debug_screenshots\`.
2. O `id` que você achou pra `SEL_LOGIN_SUCESSO` — às vezes o elemento
   certo demora um pouco a aparecer na tela (precisa de mais tempo de
   espera), ou o id muda dinamicamente a cada carregamento (nesse caso,
   me avisa que ajustamos a estratégia).
