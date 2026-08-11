"""
Teste ISOLADO de busca de nota no WTTI — assume que o login já está OK
(testado com testar_login.py) e valida só os seletores da tela de
CONSULTA DE NOTA: campo de busca, grid de resultados (gdwNotas), seleção
da linha certa por Tipo, e leitura do grid de itens (gdwProduto) + nome
do cliente + número da NF.

Dica: pra esse teste, deixe HEADLESS=false no .env — assim o Chrome abre
visível e dá pra ver exatamente onde trava, se travar.

Uso:
    python testar_busca.py <numero_ou_chave_da_nota>
"""

import sys
from scraper import scraper, NotaNaoEncontrada, ErroWtti
import config

if len(sys.argv) < 2:
    print("Uso: python testar_busca.py <numero_ou_chave_da_nota>")
    sys.exit(1)

codigo = sys.argv[1].strip()

print(f"WTTI_SEARCH_URL: {config.WTTI_SEARCH_URL}")
print(f"HEADLESS: {config.HEADLESS}")
print(f"Buscando código: {codigo}")
print("-" * 50)

try:
    dados = scraper.buscar_nota(codigo)
    print("\n✅ BUSCA FUNCIONOU!")
    print(f"Cliente: {dados['cliente']}")
    print(f"Número NF: {dados['nNF']}")
    print(f"Chave: {dados['chave'] or '(vazio, buscado pelo número curto)'}")
    print(f"Itens ({len(dados['itens'])}):")
    for item in dados["itens"]:
        print(f"  - {item['produto']} | qtd={item['qtd']} | unidade={item['unidade']}")
except NotaNaoEncontrada as e:
    print(f"\n⚠️  NOTA NÃO ENCONTRADA: {e}")
    print("Confira debug_screenshots/ pra ver o que a tela mostrava.")
    sys.exit(1)
except ErroWtti as e:
    print(f"\n❌ ERRO WTTI: {e}")
    print("Confira debug_screenshots/ pra ver o que a tela mostrava.")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERRO INESPERADO: {e}")
    sys.exit(1)
finally:
    try:
        input("\nPressione Enter pra fechar o navegador...")
    except EOFError:
        pass
    scraper.encerrar()
