"""
Baixa o arquivo tabela.csv da Tabela de Preços do CV CRM (Cota 365).

Abordagem: acessa a URL do relatório diretamente após o login,
tenta baixar o CSV via endpoint direto (/csv), senão clica no
botão "Baixar planilha" da página HTML.

Uso:
    python manage.py baixar_tabela_cvcrm
    python manage.py baixar_tabela_cvcrm --output="G:/Meu Drive/_intranet/cota365/tabela.csv"
    python manage.py baixar_tabela_cvcrm --idtabela=69
"""

import subprocess
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

DESTINO_PADRAO = r"G:\Meu Drive\_intranet\cota365\arquivos_csv\tabela.csv"

BASE_URL  = 'https://cota.cvcrm.com.br'
EMP_ID    = 3
PARAMS    = (
    'q[1|e.idempreendimento]=3'
    '&situacao[]=5&situacao[]=4&situacao[]=3&situacao[]=2&situacao[]=1'
    '&situacao_reserva[]=11&situacao_reserva[]=4&situacao_reserva[]=13'
    '&situacao_reserva[]=3&situacao_reserva[]=17&situacao_reserva[]=22'
    '&situacao_reserva[]=21&situacao_reserva[]=24&situacao_reserva[]=16'
    '&situacao_reserva[]=15&situacao_reserva[]=19&situacao_reserva[]=23'
    '&situacao_reserva[]=18&situacao_reserva[]=12&situacao_reserva[]=1'
)


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Chrome não encontrado. Use --chrome-path para indicar o executável.')


class Command(BaseCommand):
    help = 'Baixa tabela.csv da Tabela de Preços do CV CRM.'

    def add_arguments(self, parser):
        parser.add_argument('--idtabela', type=int, default=None,
                            help='ID da tabela no CV CRM (padrão: pergunta interativamente)')
        parser.add_argument('--output', type=str, default=DESTINO_PADRAO,
                            help=f'Caminho de destino (padrão: {DESTINO_PADRAO})')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        idtabela = options['idtabela']
        if idtabela is None:
            import os
            env_val = os.environ.get('CVCRM_IDTABELA', '').strip()
            if env_val:
                idtabela = int(env_val)
            else:
                raw = input('ID da tabela no CV CRM (padrão 69): ').strip()
                idtabela = int(raw) if raw else 69
        self.stdout.write(f'Usando idtabela={idtabela}')

        output_path = Path(options['output'])
        port        = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        profile_dir = options['profile_dir'] or str(
            Path(settings.BASE_DIR) / '.cvcrm_chrome_profile'
        )
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        params_com_tabela = f'q[1|t.idtabela]={idtabela}&{PARAMS}'
        url_html = f'{BASE_URL}/gestor/relatorios/tabeladepreco/html?{params_com_tabela}'
        url_csv  = f'{BASE_URL}/gestor/relatorios/tabeladepreco/csv?{params_com_tabela}'

        with sync_playwright() as p:
            browser = self._connect_or_launch(p, chrome_path, profile_dir, port, url_html)
            ctx  = browser.contexts[0]
            page = next(
                (pg for pg in ctx.pages if 'cvcrm.com.br' in pg.url),
                ctx.pages[0],
            )

            try:
                page.wait_for_load_state('load', timeout=15000)
            except Exception:
                pass

            # Garante login caso a sessão tenha expirado
            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Sessão expirada. Faça login manualmente na janela do Chrome.'
                ))
                input('Pressione ENTER após estar logado... ')
                page.wait_for_timeout(2000)

            # ── Navega para a página HTML do relatório ────────────────────────
            self.stdout.write(f'Abrindo relatório: {url_html}')
            page.goto(url_html, wait_until='load', timeout=30000)
            page.wait_for_timeout(2000)

            # ── Clica em "BAIXAR PLANILHA" e captura o download ───────────────
            self.stdout.write('Clicando em BAIXAR PLANILHA...')
            import re as _re
            btn = page.get_by_text(_re.compile('baixar planilha', _re.IGNORECASE)).first

            with page.expect_download(timeout=60000) as dl_info:
                btn.click(timeout=10000)

            download = dl_info.value
            download.save_as(str(output_path))
            self.stdout.write(self.style.SUCCESS(
                f'✓ tabela.csv salvo em: {output_path}  ({output_path.stat().st_size:,} bytes)'
            ))

    # ── Infra Chrome CDP ──────────────────────────────────────────────────────

    def _connect_or_launch(self, p, chrome_path, profile_dir, port, target_url):
        if self._debug_port_alive(port):
            self.stdout.write('Reconectando ao Chrome já aberto...')
            return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')

        self.stdout.write('Abrindo Chrome...')
        subprocess.Popen([
            chrome_path,
            f'--remote-debugging-port={port}',
            f'--user-data-dir={profile_dir}',
            target_url,
        ])
        for _ in range(15):
            time.sleep(1)
            if self._debug_port_alive(port):
                break
        else:
            raise CommandError('O Chrome não abriu a debugging port a tempo.')

        self.stdout.write(self.style.WARNING(
            '\n  Faça login manualmente na janela do Chrome que abriu.\n'
            '  (e-mail, senha e o desafio de segurança do Cloudflare)\n'
        ))
        input('  Pressione ENTER depois de estar logado e ver o painel do CV CRM... ')

        return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')

    def _debug_port_alive(self, port):
        import urllib.request
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1)
            return True
        except Exception:
            return False
