"""
Baixa o relatório de vendas (vendas.csv) do CV CRM.

Fluxo:
  1. Abre Chrome real via CDP (evita Cloudflare Turnstile)
  2. Navega para /gestor/relatorios/reservas
  3. Preenche o formulário:
       - Período: 01/01/2000 → 31/12/3000
       - Empreendimento: Cota 365
       - Situação da unidade: apenas Vendida
       - Colunas: desmarca todas, marca apenas as necessárias
  4. Clica em "Receber por e-mail" (dispara geração assíncrona)
  5. Aguarda o botão mudar para "Baixar arquivo CSV" (até 10 min)
  6. Clica e salva o arquivo

Uso:
    python manage.py baixar_vendas_cvcrm
    python manage.py baixar_vendas_cvcrm --output="G:/Meu Drive/_intranet/cota365/vendas.csv"
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

DESTINO_PADRAO = r"G:\Meu Drive\_intranet\cota365\vendas.csv"
BASE_URL        = 'https://cota.cvcrm.com.br'
RELATORIO_URL   = f'{BASE_URL}/gestor/relatorios/reservas'

# Colunas a marcar (X)
COLUNAS_DESEJADAS = [
    'Reserva', 'Situação', 'Unidade', 'M² da unidade',
    'Cliente', 'Imobiliária', 'Valor do contrato',
    'Espaços complementares', 'Data de Venda', 'Valor total',
]

# Situações da unidade a marcar
SITUACAO_UNIDADE_MARCAR   = ['Vendida']
SITUACAO_UNIDADE_DESMARCAR = ['Disponível', 'Reservada', 'Bloqueada', 'Em processo']


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Chrome não encontrado. Use --chrome-path para indicar o executável.')


class Command(BaseCommand):
    help = 'Baixa vendas.csv do relatório de reservas do CV CRM.'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=DESTINO_PADRAO,
                            help=f'Caminho de destino (padrão: {DESTINO_PADRAO})')
        parser.add_argument('--timeout-geracao', type=int, default=600,
                            help='Segundos aguardando geração do relatório (padrão: 600 = 10 min)')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        output_path = Path(options['output'])
        timeout_ms  = options['timeout_geracao'] * 1000
        port        = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        profile_dir = options['profile_dir'] or str(
            Path(settings.BASE_DIR) / '.cvcrm_chrome_profile'
        )
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = self._connect_or_launch(p, chrome_path, profile_dir, port, RELATORIO_URL)
            ctx  = browser.contexts[0]
            page = next(
                (pg for pg in ctx.pages if 'cvcrm.com.br' in pg.url),
                ctx.pages[0],
            )

            try:
                page.wait_for_load_state('load', timeout=15000)
            except Exception:
                pass

            # Garante login
            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Sessão expirada. Faça login manualmente na janela do Chrome.'
                ))
                input('Pressione ENTER após estar logado... ')
                page.wait_for_timeout(2000)

            # Navega para o relatório
            if 'relatorios/reservas' not in page.url:
                self.stdout.write(f'Navegando para {RELATORIO_URL}...')
                page.goto(RELATORIO_URL, wait_until='load', timeout=30000)
                page.wait_for_timeout(2000)

            # ── Preenche o formulário ──────────────────────────────────────────
            self._preencher_formulario(page)

            # ── Clica em "Receber por e-mail" ─────────────────────────────────
            self.stdout.write('Clicando em "Receber por e-mail"...')
            import re as _re
            btn_enviar = page.get_by_text(_re.compile('receber por e.?mail', _re.IGNORECASE)).first
            btn_enviar.click(timeout=10000)
            self.stdout.write(f'Aguardando geração (até {options["timeout_geracao"]}s)...')

            # ── Aguarda o botão mudar para "Baixar arquivo CSV" ───────────────
            btn_download = page.get_by_text(
                _re.compile('baixar arquivo csv', _re.IGNORECASE)
            ).first
            btn_download.wait_for(state='visible', timeout=timeout_ms)
            self.stdout.write('Botão "Baixar arquivo CSV" apareceu!')

            # ── Baixa o arquivo ───────────────────────────────────────────────
            with page.expect_download(timeout=60000) as dl_info:
                btn_download.click(timeout=10000)

            download = dl_info.value
            download.save_as(str(output_path))
            self.stdout.write(self.style.SUCCESS(
                f'✓ vendas.csv salvo em: {output_path}  ({output_path.stat().st_size:,} bytes)'
            ))

    def _preencher_formulario(self, page):
        import re as _re

        # ── Datas ─────────────────────────────────────────────────────────────
        self.stdout.write('Preenchendo datas...')
        # Tenta diferentes seletores para o campo "De"
        for sel_de in ['[name*="data_ini"]', '[id*="data_ini"]', '[placeholder*="De"]',
                       'input[name*="de"]', 'input[id*="de"]']:
            if page.locator(sel_de).count() > 0:
                page.locator(sel_de).first.fill('01/01/2000')
                break
        else:
            self._preencher_data_por_label(page, 'De', '01/01/2000')

        for sel_ate in ['[name*="data_fim"]', '[id*="data_fim"]', '[placeholder*="Até"]',
                        'input[name*="ate"]', 'input[id*="ate"]']:
            if page.locator(sel_ate).count() > 0:
                page.locator(sel_ate).first.fill('31/12/3000')
                break
        else:
            self._preencher_data_por_label(page, 'Até', '31/12/3000')

        # ── Empreendimento ────────────────────────────────────────────────────
        self.stdout.write('Selecionando empreendimento Cota 365...')
        self._selecionar_empreendimento(page, 'Cota 365')

        # ── Situação da unidade ───────────────────────────────────────────────
        self.stdout.write('Configurando situação da unidade...')
        for label_txt in SITUACAO_UNIDADE_DESMARCAR:
            self._set_checkbox_por_label(page, label_txt, False)
        for label_txt in SITUACAO_UNIDADE_MARCAR:
            self._set_checkbox_por_label(page, label_txt, True)

        # ── Colunas de exibição ───────────────────────────────────────────────
        self.stdout.write('Configurando colunas...')
        # Desmarca todas via botão "Desmarcar todos"
        btn_desmarcar = page.get_by_text(_re.compile('desmarcar todos', _re.IGNORECASE)).first
        if btn_desmarcar.count() > 0:
            btn_desmarcar.click()
            page.wait_for_timeout(500)
        # Marca as colunas desejadas
        for col in COLUNAS_DESEJADAS:
            self._set_checkbox_por_label(page, col, True)

        page.wait_for_timeout(500)

    def _preencher_data_por_label(self, page, label_txt, valor):
        """Encontra input pelo texto do label adjacente."""
        label = page.locator(f'label', has_text=label_txt).first
        if label.count() > 0:
            for_id = label.get_attribute('for')
            if for_id:
                page.locator(f'#{for_id}').fill(valor)

    def _selecionar_empreendimento(self, page, nome):
        """Tenta select nativo, depois Select2, depois input text."""
        # Select nativo
        sel = page.locator('select').filter(
            has=page.locator(f'option:has-text("{nome}")')
        ).first
        if sel.count() > 0:
            sel.select_option(label=nome)
            return

        # Select2 / searchable — clica no container e digita
        containers = page.locator('.select2-container, [class*="select2"]').all()
        for container in containers:
            if container.is_visible():
                container.click()
                page.wait_for_timeout(300)
                search = page.locator('.select2-search__field, .select2-input').first
                if search.is_visible():
                    search.fill(nome)
                    page.wait_for_timeout(500)
                    option = page.locator(f'.select2-results__option:has-text("{nome}")').first
                    if option.is_visible():
                        option.click()
                        return
                page.keyboard.press('Escape')

        self.stdout.write(self.style.WARNING(
            f'  Não conseguiu selecionar empreendimento "{nome}" automaticamente.'
        ))

    def _set_checkbox_por_label(self, page, label_txt, checked: bool):
        """Marca/desmarca checkbox pelo texto do label."""
        # Tenta label que contém exatamente o texto
        for loc in [
            page.locator(f'label', has_text=label_txt),
            page.locator(f'label:has-text("{label_txt}")'),
        ]:
            if loc.count() > 0:
                cb = loc.first.locator('input[type="checkbox"]')
                if cb.count() == 0:
                    # label externo — busca pelo for
                    for_id = loc.first.get_attribute('for')
                    if for_id:
                        cb = page.locator(f'#{for_id}')
                if cb.count() > 0:
                    if checked and not cb.is_checked():
                        cb.check()
                    elif not checked and cb.is_checked():
                        cb.uncheck()
                    return

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
        input('  Pressione ENTER depois de estar logado... ')
        return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')

    def _debug_port_alive(self, port):
        import urllib.request
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1)
            return True
        except Exception:
            return False
