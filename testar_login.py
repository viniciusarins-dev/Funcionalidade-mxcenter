"""
Teste ISOLADO de login no WTTI — não busca nota nenhuma, só confirma
que usuário/senha estão certos e que os seletores de login batem com
a tela real.

Dica: pra esse primeiro teste, deixe HEADLESS=false no .env — assim o
Chrome abre visível na sua tela e você literalmente vê o que está
acontecendo (ou travando) em tempo real.

Uso:
    python testar_login.py
"""

import sys
from scraper import scraper, ErroWtti

print(f"Tentando logar em: {scraper.__class__.__module__}")
import config
print(f"WTTI_LOGIN_URL: {config.WTTI_LOGIN_URL}")
print(f"WTTI_USER: {config.WTTI_USER}")
print(f"HEADLESS: {config.HEADLESS}")
print("-" * 50)

try:
    scraper.login()
    print("\n✅ LOGIN FUNCIONOU!")
    print("Os seletores de login (SEL_LOGIN_*) estão corretos.")
    print("Próximo passo: ajustar os seletores da tela de busca de nota.")
except ErroWtti as e:
    print(f"\n❌ LOGIN FALHOU: {e}")
    print("\nPossíveis causas:")
    print("  1. Usuário ou senha errados no .env")
    print("  2. SEL_LOGIN_USERNAME / SEL_LOGIN_PASSWORD / SEL_LOGIN_SUBMIT")
    print("     não correspondem aos campos reais da tela de login")
    print("  3. SEL_LOGIN_SUCESSO não corresponde a nenhum elemento que")
    print("     aparece DEPOIS do login bem-sucedido")
    print("\nSe salvou um screenshot, confira a pasta debug_screenshots/")
    print("pra ver exatamente o que a tela mostrava no momento do erro.")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERRO INESPERADO: {e}")
    print("\nSe for erro relacionado a 'chromedriver' ou 'chrome not found',")
    print("confirme que o Google Chrome está instalado nessa máquina.")
    sys.exit(1)
finally:
    try:
        input("\nPressione Enter pra fechar o navegador...")
    except EOFError:
        pass
    scraper.encerrar()
