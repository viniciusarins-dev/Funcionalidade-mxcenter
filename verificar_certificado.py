"""
Verificação local do certificado digital, ANTES de rodar a API de verdade.

Roda 100% na sua máquina — a senha do certificado nunca precisa ser
digitada em lugar nenhum além daqui (lida do seu .env local).

Uso:
    python3 verificar_certificado.py

O que ele confere:
  1. Se a senha do .env realmente abre o certificado.
  2. Se o CNPJ dentro do certificado bate com EMPRESA_CNPJ no .env.
  3. Se o certificado não está vencido (ou perto de vencer).
"""

import sys
import datetime

from cryptography.hazmat.primitives.serialization import pkcs12

import config


def main():
    print(f"Lendo certificado em: {config.CERT_PATH}")

    try:
        with open(config.CERT_PATH, "rb") as f:
            dados_pfx = f.read()
    except FileNotFoundError:
        print(f"❌ Arquivo não encontrado: {config.CERT_PATH}")
        print("   Confira o caminho em CERT_PATH no seu .env.")
        sys.exit(1)

    try:
        chave_privada, certificado, cadeia = pkcs12.load_key_and_certificates(
            dados_pfx,
            config.CERT_PASSWORD.encode("utf-8"),
        )
    except Exception as e:
        print(f"❌ Não foi possível abrir o certificado com a senha fornecida: {e}")
        print("   Confira CERT_PASSWORD no .env.")
        sys.exit(1)

    if certificado is None:
        print("❌ Senha correta, mas nenhum certificado foi encontrado no arquivo.")
        sys.exit(1)

    print("✅ Certificado aberto com sucesso com a senha do .env.\n")

    # --- Dados do certificado ------------------------------------------
    subject = certificado.subject.rfc4514_string()
    print(f"Titular (subject): {subject}")

    not_before = certificado.not_valid_before_utc
    not_after = certificado.not_valid_after_utc
    agora = datetime.datetime.now(datetime.timezone.utc)

    print(f"Válido de:  {not_before.date()}")
    print(f"Válido até: {not_after.date()}")

    dias_restantes = (not_after - agora).days
    if agora > not_after:
        print(f"❌ CERTIFICADO VENCIDO há {-dias_restantes} dia(s)!")
        sys.exit(1)
    elif dias_restantes < 30:
        print(f"⚠️  Atenção: certificado vence em {dias_restantes} dia(s). Considere renovar.")
    else:
        print(f"✅ Certificado válido por mais {dias_restantes} dia(s).")

    # --- Confere se o CNPJ do certificado bate com o do .env ------------
    # Certificados e-CNPJ costumam trazer o CNPJ no campo subject, geralmente
    # dentro do CN, no formato "NOME DA EMPRESA:CNPJ" ou similar.
    cnpj_env = "".join(filter(str.isdigit, config.EMPRESA_CNPJ))
    digitos_no_subject = "".join(filter(str.isdigit, subject))

    print(f"\nEMPRESA_CNPJ configurado no .env: {cnpj_env}")

    if cnpj_env and cnpj_env in digitos_no_subject:
        print("✅ O CNPJ configurado no .env aparece no certificado. Consistente.")
    else:
        print(
            "⚠️  Não encontrei esse CNPJ exato dentro do subject do certificado.\n"
            "   Isso pode ser só uma diferença de formatação — confira manualmente\n"
            f"   o campo 'Titular' acima e confirme se o CNPJ bate com {cnpj_env}."
        )

    print("\nSe tudo acima estiver ✅, o certificado está pronto para uso na API.")


if __name__ == "__main__":
    main()
