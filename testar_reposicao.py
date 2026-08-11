"""
Teste ISOLADO da sugestão de reposição — assume que o login já está OK
(testado com testar_login.py) e valida os seletores das duas telas novas:

  - Relatório de Ranking de Produtos (saída do mês)
  - Manutenção de Estoque por Filial (estoque cadastrado no sistema)

Esses dois ainda NÃO foram inspecionados no HTML real do WTTI — os
seletores em config.py/.env são só um palpite razoável (ver GUIA_SELETORES.md,
Passo 7). É bem provável que precisem de ajuste na primeira rodada.

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

print(f"WTTI_RANKING_URL: {config.WTTI_RANKING_URL}")
print(f"WTTI_ESTOQUE_URL: {config.WTTI_ESTOQUE_URL}")
print(f"HEADLESS: {config.HEADLESS}")
print(f"Buscando código: {codigo}")
print("-" * 50)

try:
    print("\n[1/2] Consultando saída do mês (Ranking de Produtos)...")
    saida_mes = scraper.buscar_saida_mes_produto(codigo)
    print(f"      Saída do mês: {saida_mes}")

    print("\n[2/2] Consultando estoque no sistema (Manutenção de Estoque)...")
    estoque = scraper.buscar_estoque_produto(codigo)
    print(f"      Estoque no sistema: {estoque}")

    print("\n✅ CONSULTA FUNCIONOU!")
    print(f"Saída do mês: {saida_mes} | Estoque no sistema: {estoque}")
    print(
        "\nSe os dois números batem com o que você vê manualmente no WTTI, os "
        "seletores estão corretos. Se vieram 0 e você esperava outro valor, "
        "confira debug_screenshots/ e ajuste os seletores SEL_RANKING_* / "
        "SEL_ESTOQUE_* (veja GUIA_SELETORES.md, Passo 7)."
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
