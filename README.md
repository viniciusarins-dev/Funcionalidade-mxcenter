# API de Conferência de Pedidos — Consulta direta à SEFAZ

API em Flask que recebe a **chave de acesso (44 dígitos)** da nota, consulta
**diretamente a SEFAZ** (webservice oficial `NFeDistribuiçãoDFe`, operação
`consChNFe`) usando o certificado digital da empresa, e devolve os itens da
nota em JSON — sem depender do WTTI, de Selenium ou de qualquer automação de
tela.

## Por que essa abordagem em vez de automatizar o WTTI?

- É o **serviço oficial do governo**: você consulta a fonte da verdade, não
  uma tela de terceiro que pode mudar de layout a qualquer atualização.
- Não quebra por timing de navegador, popup, iframe ou postback — é uma
  chamada HTTP/SOAP direta.
- Já retorna o XML completo da nota (com todos os itens), sem precisar
  raspar HTML nem mapear seletor de grid.

**A limitação importante:** essa consulta só funciona com a **chave de
acesso completa (44 dígitos)** — a SEFAZ não indexa notas pelo número curto
da NF (só a chave é única nacionalmente). Isso é perfeito pro fluxo normal
de leitor de código de barras, mas quer dizer que a digitação manual do
"número da nota" (sem o leitor) não tem como funcionar por essa via. Se você
precisar cobrir esse caso, a saída é manter o upload de XML como
complemento (o app já suporta isso).

## 1. Pré-requisitos

- **Certificado digital da empresa** (e-CNPJ ou e-CPF), tipo **A1**, ou seja,
  um arquivo `.pfx`/`.p12` (não o A3, que fica num token físico e não pode
  ser lido programaticamente sem drivers específicos do token).
- Python 3.10+.

## 2. Instalação

```bash
cd api-conferencia-wtti
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. Configuração

```bash
cp .env.example .env
```

Edite o `.env`:

- `CERT_PATH` — caminho completo pro arquivo `.pfx` do certificado.
- `CERT_PASSWORD` — senha desse certificado.
- `EMPRESA_CNPJ` — CNPJ da empresa, só números (precisa ser o mesmo CNPJ do
  certificado).
- `UF_EMPRESA` — sigla da UF (ex: `SC`). Pode deixar em branco: nesse caso o
  código deriva automaticamente dos 2 primeiros dígitos da própria chave
  consultada.
- `AMBIENTE` — comece com `homologacao` pra testar sem risco, depois troque
  pra `producao`.

**O `.env` nunca deve ir pro Git** (ele tem a senha do certificado da
empresa).

## 4. Verificando o certificado antes de ir pra produção

Antes de rodar a API de verdade, confirme que o certificado está OK:

```bash
python3 verificar_certificado.py
```

Esse script confere, só na sua máquina (a senha nunca sai do seu `.env`
local):
- se a senha realmente abre o `.pfx`;
- se o CNPJ dentro do certificado bate com `EMPRESA_CNPJ` no `.env`;
- se o certificado não está vencido (ou perto de vencer).

## 5. Testando a consulta na SEFAZ

Recomendo testar primeiro com `AMBIENTE=homologacao` e uma chave de nota que
você sabe que existe (uma nota real já emitida pela empresa). No ambiente de
homologação, a SEFAZ simula as respostas, então **não** é preciso usar uma
chave de teste "fake" — precisa ser uma chave real da sua própria empresa,
já que a consulta valida se o CNPJ do certificado tem relação com aquele
documento.

## 6. Hospedando na nuvem (acesso de qualquer lugar, com HTTPS)

Se você precisa acessar de fora da rede da empresa (4G/5G, qualquer Wi-Fi),
a rede local não resolve — é preciso hospedar a API (com o certificado) num
servidor na nuvem, com HTTPS de verdade. Recomendo o **Render.com**: tem
plano gratuito, HTTPS automático, e um recurso chamado "Secret Files" feito
sob medida pra guardar o `.pfx` sem colocar ele no Git.

### 6.1. Suba o projeto pro GitHub (sem o certificado nem o .env)

O `.gitignore` já está configurado pra nunca versionar `.env` e `*.pfx`.

```bash
cd api-conferencia-wtti
git init
git add .
git commit -m "API de conferência de pedidos"
```

Crie um repositório vazio em https://github.com/new (pode ser privado) e
depois:

```bash
git remote add origin https://github.com/SEU-USUARIO/SEU-REPOSITORIO.git
git branch -M main
git push -u origin main
```

Se você não tem conta no GitHub, é gratuito e leva 2 minutos em
https://github.com/signup.

### 6.2. Crie o Web Service no Render

1. Crie uma conta em https://render.com (dá pra entrar direto com GitHub).
2. **New +** → **Web Service** → conecte o repositório que você acabou de subir.
3. Configure:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT` (o Render já
     detecta isso sozinho pelo `Procfile`, mas confira se preencheu certo)
   - **Instance Type:** Free (pra começar; veja a nota sobre "cold start" abaixo)

### 6.3. Suba o certificado como Secret File

Na aba **Environment** do serviço no Render, procure **Secret Files**:

- **Filename (caminho no servidor):** `/etc/secrets/certificado.pfx`
- **Contents:** faça upload do seu `certificado.pfx`

Isso guarda o certificado de forma criptografada, fora do Git, só acessível
pelo próprio serviço em tempo de execução.

### 6.4. Configure as variáveis de ambiente

Ainda na aba **Environment**, em **Environment Variables**, adicione:

| Variável         | Valor                                    |
|------------------|-------------------------------------------|
| `CERT_PATH`      | `/etc/secrets/certificado.pfx`             |
| `CERT_PASSWORD`  | a senha real do certificado                |
| `EMPRESA_CNPJ`   | `15532713000173`                           |
| `UF_EMPRESA`     | `SC` (ou deixe vazio)                      |
| `AMBIENTE`       | `producao`                                 |
| `API_KEY`        | invente uma chave forte (ex: gere com `python3 -c "import secrets; print(secrets.token_hex(24))"`) |
| `CORS_ORIGINS`   | `*` (ou o domínio específico, se preferir) |
| `CACHE_TTL_SECONDS` | `300`                                    |

Não precisa configurar `PORT` — o Render já injeta essa variável sozinho.

### 6.5. Deploy e teste

Clique em **Create Web Service**. O Render vai instalar as dependências e
subir a aplicação. Ao terminar, você recebe uma URL tipo:

```
https://sua-api-conferencia.onrender.com
```

Teste:
- `https://sua-api-conferencia.onrender.com/api/health` → deve retornar `{"status":"ok"}`.
- `https://sua-api-conferencia.onrender.com/` → deve abrir a tela de conferência.

Como tudo (tela + API) fica no mesmo domínio HTTPS, o `window.location.origin`
já resolve a URL da API automaticamente — nenhuma edição extra é necessária,
e não há problema de "mixed content" (tudo é HTTPS).

Do celular, em qualquer rede (4G/5G ou Wi-Fi), é só acessar essa URL e,
se quiser, "Adicionar à tela inicial".

### 6.6. Atenção ao plano gratuito

- O plano **Free** do Render "hiberna" o serviço após um tempo sem uso — a
  primeira requisição depois disso demora ~30-60 segundos pra "acordar" o
  servidor. Pra uso constante numa bancada, isso pode incomodar; se for o
  caso, o plano pago mais barato (a partir de ~US$7/mês) mantém o serviço
  sempre ativo.
- Guarde o `API_KEY` gerado em local seguro — sem ele configurado, qualquer
  pessoa que descobrir a URL pública conseguiria consultar notas fiscais da
  empresa.

## 7. Rodando localmente (alternativa, sem nuvem)

Se quiser rodar localmente em vez de hospedar na nuvem (ex: só na rede da
empresa), o processo é mais simples:

```bash
python3 app.py
```

- `http://localhost:5000/` → a tela de conferência.
- `http://localhost:5000/api/...` → a API.

### Acessando pelo celular (mesma rede Wi-Fi)

1. **Descubra o IP local** da máquina onde a API está rodando:
   - Windows: abra o Prompt de Comando e digite `ipconfig` → veja o
     "Endereço IPv4" (algo como `192.168.0.15`).
   - Mac/Linux: `ifconfig` ou `ip a` (procure a interface Wi-Fi/Ethernet).
2. **Libere a porta no firewall**, se for pedido — no Windows, na primeira
   vez que rodar `python3 app.py`, pode aparecer um aviso do Firewall do
   Windows pedindo permissão; escolha "Permitir acesso" em redes privadas.
3. No **celular, conectado na mesma rede Wi-Fi**, abra o navegador e acesse:
   ```
   http://192.168.0.15:5000/
   ```
   (troque pelo IP real que você descobriu no passo 1).
4. Teste primeiro `http://192.168.0.15:5000/api/health` — se aparecer
   `{"status":"ok"}`, a rede está OK e o resto vai funcionar.

**Atenção:** se o IP da máquina mudar (o que pode acontecer ao reiniciar o
roteador), o link salvo no celular para de funcionar. Se isso incomodar, dá
pra reservar um IP fixo pra essa máquina nas configurações do roteador
(procure por "DHCP reservation" ou "IP fixo" no painel do roteador).

## 8. Endpoints da API

- `GET /api/health` — verificação simples de que a API está no ar.
- `GET /api/notas/<chave>` — busca a nota pela chave de 44 dígitos. Retorna:
  ```json
  {
    "chave": "35240112345678000199550010000012341123456789",
    "nNF": "1234",
    "cliente": "Nome do Cliente",
    "itens": [
      { "produto": "Nome do produto", "qtd": 10, "unidade": "UN" }
    ]
  }
  ```
  - `400` se o código enviado não tiver 44 dígitos (ex: número curto de NF).
  - `404` se a SEFAZ não localizar nenhum documento pra essa chave (`cStat=137`).
  - `401` se `API_KEY` estiver configurada e o header `X-API-Key` não bater.
  - `502` se a SEFAZ recusar a consulta por outro motivo (throttling,
    problema de certificado, etc. — a mensagem de erro (`xMotivo`) vem
    junto na resposta).
  - `500` em erro interno inesperado.

## 9. Conectando o front-end à API

Isso já vem pronto: como a tela é servida pelo mesmo Flask (seção 6), o
`CONFIG.API_BASE_URL` dentro do `static/index.html` já está configurado para
usar automaticamente `window.location.origin` — ou seja, funciona tanto em
`http://localhost:5000` quanto em `http://192.168.0.15:5000`, sem precisar
editar nada.

A única coisa que você precisa ajustar manualmente é se ativou `API_KEY` no
`.env` — nesse caso, edite o `fetch()` da função `buscarPedidoAPI()` dentro
de `static/index.html` para enviar o header:

```javascript
headers: {
  'Accept': 'application/json',
  'X-API-Key': 'a-mesma-chave-que-voce-colocou-no-.env',
}
```

## 10. Limitações importantes (leia antes de colocar em produção)

- **Só funciona com a chave completa (44 dígitos).** Ver seção acima.
- **A SEFAZ limita consultas repetidas pela mesma chave** num intervalo
  curto (política anti-abuso do serviço). O cache de 5 minutos do `app.py`
  já evita boa parte disso; se um operador bipar a mesma nota várias vezes
  seguidas, considere aumentar `CACHE_TTL_SECONDS`.
- **O CNPJ da consulta precisa ser uma das partes da nota** (emitente,
  destinatário, transportador, etc.). Como a empresa é a emitente das
  próprias notas, isso já é atendido naturalmente — mas não vai funcionar
  se você tentar consultar uma nota de um terceiro qualquer.
- **Certificado A1 apenas.** Se a empresa só tiver certificado A3 (token
  USB/cartão), essa abordagem programática não funciona sem um servidor
  com o token conectado fisicamente e drivers específicos — nesse caso,
  vale reconsiderar as outras alternativas (XML local, ou a versão via
  Selenium que ficou registrada no histórico da conversa, arquivo
  `scraper.py`, ainda presente neste projeto caso queira retomar).
- **Se hospedar na nuvem, proteja com `API_KEY` forte.** Como o serviço
  fica acessível publicamente, o `API_KEY` é o que impede qualquer pessoa
  que descubra a URL de consultar notas fiscais da empresa. Se rodar só na
  rede interna, mantenha isso restrito à rede local mesmo assim.

## 11. Estrutura dos arquivos

```
api-conferencia-wtti/
├── app.py                    # rotas Flask (API + serve a tela em /)
├── sefaz_client.py            # cliente do webservice NFeDistribuicaoDFe (SEFAZ)
├── verificar_certificado.py   # checagem local do certificado antes de ir pra produção
├── certificado.pfx            # certificado digital da empresa (NÃO versionar)
├── static/
│   └── index.html             # a tela de conferência (bancada), servida em "/"
├── Procfile                   # comando de start usado pelo Render (gunicorn)
├── .gitignore                 # garante que .env e *.pfx nunca vão pro Git
├── scraper.py                 # [legado] automação Selenium do WTTI — não usado por padrão
├── config.py                  # todas as configurações via variáveis de ambiente
├── requirements.txt
├── .env / .env.example
└── README.md
```
