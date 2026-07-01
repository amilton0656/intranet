"""
Sincroniza tabelas de vendas PDF para a intranet.

Uso:
    python scripts/sincronizar_tabelas.py

O script:
  1. Lê todos os PDFs de PASTA_ORIGEM
  2. Remove o sufixo de mês/ano do nome  (ex. " - Julho 2026" → "")
  3. Faz login na intranet e envia cada arquivo para /uploads/pdfs/
"""

import re
import sys
import getpass
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Instale o requests:  pip install requests")

# ── Configurações ──────────────────────────────────────────────────────────────

PASTA_ORIGEM = Path(r"G:\Drives compartilhados\Tabelas de Vendas - Corretor")
INTRANET_URL = "https://apicota.com.br"   # sem barra no final
USUARIO      = "amilton"                  # altere se necessário

# ── Regex que detecta qualquer mês/ano no final do nome ───────────────────────

_MESES = (
    r"Janeiro|Fevereiro|Mar[çc]o|Abril|Maio|Junho|"
    r"Julho|Agosto|Setembro|Outubro|Novembro|Dezembro"
)
_PADRAO = re.compile(
    rf"\s*-\s+(?:{_MESES})\s+\d{{4}}\s*",
    re.IGNORECASE,
)

def strip_mes(nome_arquivo: str) -> str:
    """Remove ' - Julho 2026' (ou qualquer mês/ano) do nome do arquivo."""
    stem   = Path(nome_arquivo).stem
    sufixo = Path(nome_arquivo).suffix
    novo   = _PADRAO.sub("", stem).rstrip(" -").strip()
    return novo + sufixo


# ── Upload ─────────────────────────────────────────────────────────────────────

def login(session: "requests.Session", senha: str) -> bool:
    login_url = f"{INTRANET_URL}/accounts/login/"
    r = session.get(login_url, timeout=15)
    r.raise_for_status()

    csrf = session.cookies.get("csrftoken", "")
    r = session.post(
        login_url,
        data={"username": USUARIO, "password": senha, "csrfmiddlewaretoken": csrf, "next": "/"},
        headers={"Referer": login_url, "X-CSRFToken": csrf},
        timeout=15,
        allow_redirects=True,
    )
    # Login OK se não voltou para /login/
    return "/login/" not in r.url


def enviar_pdf(session: "requests.Session", caminho: Path, nome_destino: str) -> bool:
    upload_url = f"{INTRANET_URL}/uploads/pdfs/"
    r = session.get(upload_url, timeout=10)
    csrf = session.cookies.get("csrftoken", "")

    with open(caminho, "rb") as f:
        r = session.post(
            upload_url,
            data={"action": "upload", "csrfmiddlewaretoken": csrf},
            files={"arquivo": (nome_destino, f, "application/pdf")},
            headers={"Referer": upload_url},
            timeout=60,
        )
    return r.ok


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Sincronizador de Tabelas de Vendas — Intranet")
    print("=" * 60)

    # Verifica pasta
    if not PASTA_ORIGEM.exists():
        sys.exit(f"\nPasta não encontrada:\n  {PASTA_ORIGEM}\n\nVerifique se o Google Drive está sincronizado.")

    pdfs = sorted(PASTA_ORIGEM.glob("*.pdf"))
    if not pdfs:
        sys.exit(f"\nNenhum PDF encontrado em:\n  {PASTA_ORIGEM}")

    print(f"\nPasta: {PASTA_ORIGEM}")
    print(f"Arquivos encontrados: {len(pdfs)}\n")

    # Mostra preview dos renomes
    renomes = []
    for pdf in pdfs:
        novo = strip_mes(pdf.name)
        renomes.append((pdf, novo))
        status = "  (sem alteração)" if novo == pdf.name else ""
        print(f"  {pdf.name}")
        print(f"    → {novo}{status}")

    print()
    confirmar = input("Enviar para a intranet? [s/N] ").strip().lower()
    if confirmar != "s":
        print("Cancelado.")
        return

    senha = getpass.getpass(f"\nSenha do usuário '{USUARIO}': ")

    session = requests.Session()

    print("\nFazendo login...")
    if not login(session, senha):
        sys.exit("Login falhou. Verifique usuário e senha.")
    print("Login OK.\n")

    erros = []
    for caminho, nome_destino in renomes:
        print(f"  Enviando: {nome_destino} ... ", end="", flush=True)
        try:
            ok = enviar_pdf(session, caminho, nome_destino)
            print("OK" if ok else "ERRO (resposta não-OK)")
            if not ok:
                erros.append(nome_destino)
        except Exception as e:
            print(f"ERRO: {e}")
            erros.append(nome_destino)

    print()
    if erros:
        print(f"Concluído com {len(erros)} erro(s):")
        for e in erros:
            print(f"  ✗ {e}")
    else:
        print(f"Concluído! {len(renomes)} arquivo(s) enviado(s) com sucesso.")


if __name__ == "__main__":
    main()
