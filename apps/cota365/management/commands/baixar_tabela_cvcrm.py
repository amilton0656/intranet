"""
Baixa o arquivo tabela.csv da Tabela de Preços do CV CRM (Cota 365).

Fluxo automatizado:
  1. Abre Chrome real via CDP (evita Cloudflare Turnstile — mesma técnica do importar_cvcrm)
  2. Pede login manual na primeira vez; sessão fica salva entre execuções
  3. Navega para Empreendimentos → Cota 365 → Tabela de Preços
  4. Localiza o item indicado (padrão: contém "R00" ou "Tabela Curta")
  5. Clica em Opções → Gerar/Imprimir → Baixar planilha
  6. Salva o arquivo no destino configurado

Uso:
    python manage.py baixar_tabela_cvcrm
    python manage.py baixar_tabela_cvcrm --output="G:/Meu Drive/_intranet/cota365/tabela.csv"
    python manage.py baixar_tabela_cvcrm --busca="Tabela Curta"
    python manage.py baixar_tabela_cvcrm --empreendimento=3
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

DESTINO_PADRAO = r"G:\Meu Drive\_intranet\cota365\tabela.csv"


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError(
        'Chrome não encontrado. Use --chrome-path para indicar o executável.'
    )


class Command(BaseCommand):
    help = 'Baixa tabela.csv da Tabela de Preços do CV CRM.'

    def add_arguments(self, parser):
        parser.add_argument('--empreendimento', type=int, default=3,
                            help='ID do empreendimento no CV CRM (padrão: 3 = Cota 365)')
        parser.add_argument('--busca', type=str, default='R00',
                            help='Texto para localizar a tabela na lista (padrão: "R00")')
        parser.add_argument('--output', type=str, default=DESTINO_PADRAO,
                            help=f'Caminho de destino do arquivo (padrão: {DESTINO_PADRAO})')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        emp_id      = options['empreendimento']
        busca       = options['busca']
        output_path = Path(options['output'])
        port        = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        profile_dir = options['profile_dir'] or str(
            Path(settings.BASE_DIR) / '.cvcrm_chrome_profile'
        )
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        base       = 'https://cota.cvcrm.com.br'
        admin_url  = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/administrar'

        with sync_playwright() as p:
            browser = self._connect_or_launch(p, chrome_path, profile_dir, port, admin_url)
            ctx  = browser.contexts[0]
            page = next(
                (pg for pg in ctx.pages if 'cvcrm.com.br' in pg.url),
                ctx.pages[0],
            )

            try:
                page.wait_for_load_state('load', timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(1500)

            # Garante login caso a sessão tenha expirado
            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Sessão expirada. Faça login manualmente na janela do Chrome.'
                ))
                input('Pressione ENTER após estar logado... ')
                page.wait_for_timeout(2000)

            # ── Navega para o empreendimento ──────────────────────────────────
            if f'empreendimentos/{emp_id}' not in page.url:
                self.stdout.write(f'Navegando para o empreendimento {emp_id}...')
                page.goto(admin_url, wait_until='load', timeout=30000)
                page.wait_for_timeout(1500)

            # ── Clica na aba "Tabela de Preços" ──────────────────────────────
            self.stdout.write('Abrindo aba Tabela de Preços...')
            tab = (
                page.get_by_role('link', name='Tabela de preços')
                .or_(page.get_by_role('tab', name='Tabela de preços'))
                .or_(page.locator('a', has_text='Tabela de preços'))
                .first
            )
            tab.click(timeout=10000)
            page.wait_for_timeout(2000)

            # ── Localiza a linha com o texto de busca ─────────────────────────
            self.stdout.write(f'Procurando item com "{busca}"...')
            linha = page.locator('tr', has=page.locator(f'text={busca}')).first
            linha.wait_for(timeout=10000)

            # ── Clica no botão "Opções" da linha ─────────────────────────────
            btn_opcoes = linha.get_by_role('button').or_(
                linha.locator('[class*="opcoes"], [data-toggle="dropdown"], .dropdown-toggle')
            ).first
            btn_opcoes.click(timeout=5000)
            page.wait_for_timeout(800)

            # ── Clica em "Gerar / Imprimir" ───────────────────────────────────
            page.get_by_text('Gerar').or_(page.get_by_text('Gerar / Imprimir')).first.click(timeout=5000)
            page.wait_for_timeout(1500)

            # ── Clica em "Baixar planilha" e captura o download ───────────────
            self.stdout.write('Aguardando download...')
            with page.expect_download(timeout=60000) as dl_info:
                page.get_by_text('Baixar planilha').or_(
                    page.get_by_role('link', name='Baixar planilha')
                ).first.click(timeout=10000)

            download = dl_info.value
            download.save_as(str(output_path))
            self.stdout.write(self.style.SUCCESS(
                f'✓ tabela.csv salvo em: {output_path}'
            ))

    # ── Infra Chrome CDP (igual ao importar_cvcrm) ────────────────────────────

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
