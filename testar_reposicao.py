"""
Teste ISOLADO da sugestão de reposição — assume que o login já está OK
(testado com testar_login.py) e valida os seletores do Relatório Produto
x Saldo (estoque atual + médias mensais de saída e compra, calculadas
desde 01/01 do ano atual até hoje).

Seletores confirmados por inspeção do HTML real em 2026-08-11 (ver
GUIA_SELETORES.md, Passo 7).

Dica: deixe HEADLESS=false no .env pra ver o Chrome abrindo e identificar
exatamente onde a busca desvia do esperado.

Uso:
    python testar_reposicao.py <codigo_do_produto>
"""

import sys

# No Windows, o console usa cp1252 por padrão, que não imprime os emojis
# (✅/❌) usados abaixo — força saída em UTF-8 sem depender de
# PYTHONIOENCODING ser setado externamente.
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from scraper import scraper, ProdutoNaoEncontrado, ErroWtti
import config

if len(sys.argv) < 2:
    print("Uso: python testar_reposicao.py <codigo_do_produto>")
    sys.exit(1)

codigo = sys.argv[1].strip()

print(f"WTTI_SALDO_URL: {config.WTTI_SALDO_URL}")
print(f"HEADLESS: {config.HEADLESS}")
print(f"Buscando código: {codigo}")
print("-" * 50)

try:
    resultado = scraper.buscar_reposicao_produto(codigo)

    print("\n✅ CONSULTA FUNCIONOU!")
    print(f"Produto: {resultado['produto']}")
    print(f"Estoque no sistema (s/ reservas): {resultado['estoque']}")
    print(f"Saída média/mês (desde 01/01): {resultado['saida_media_mensal']}")
    print(f"Compra média/mês (desde 01/01): {resultado['compra_media_mensal']}")
    print(
        "\nSe os números batem com o que você vê manualmente no WTTI, os "
        "seletores estão corretos. Se vier estoque errado, confira "
        "COL_SALDO_CODIGO/COL_SALDO_ESTOQUE_SEM_RESERVA; se as médias "
        "vierem erradas, confira COL_HISTORICO_TIPO/QTD e os campos de data "
        "SEL_SALDO_DATA_INICIAL/FINAL (veja GUIA_SELETORES.md, Passo 7)."
    )

except ProdutoNaoEncontrado as e:
    print(f"\n⚠️  PRODUTO NÃO ENCONTRADO: {e}")
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
