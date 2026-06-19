"""
Baixa o relatório de vendas (vendas.csv) do CV CRM.

Fluxo:
  1. Abre Chrome real via CDP (evita Cloudflare Turnstile)
  2. Navega para /gestor/relatorios/reservas
  3. Limpa todos os campos do formulário
  4. Preenche o formulário:
       - Período: 01/01/2000 → 01/01/3000
       - Empreendimento: Cota 365
       - Situação da reserva: apenas Vendida
       - Colunas: desmarca todas, marca apenas as necessárias
  5. Clica em "Receber por e-mail" (dispara geração assíncrona)
  6. Na próxima tela aguarda e clica em "CLIQUE AQUI PARA BAIXAR O ARQUIVO GERADO"
  7. Salva o arquivo

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

            # Sempre navega para o relatório (garante formulário limpo)
            self.stdout.write(f'Navegando para {RELATORIO_URL}...')
            page.goto(RELATORIO_URL, wait_until='load', timeout=30000)
            page.wait_for_timeout(2000)

            # Verifica login novamente (a navegação pode ter redirecionado)
            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Sessão expirada. Faça login manualmente na janela do Chrome.'
                ))
                input('Pressione ENTER após estar logado... ')
                page.goto(RELATORIO_URL, wait_until='load', timeout=30000)
                page.wait_for_timeout(2000)

            # ── Preenche o formulário ──────────────────────────────────────────
            self._preencher_formulario(page)

            # ── Clica em "Receber por e-mail" e captura a nova aba ───────────
            import re as _re
            btn_pattern = _re.compile(r'receber por e.?mail', _re.IGNORECASE)

            btn_enviar = None
            for role in ('button', 'link'):
                loc = page.get_by_role(role, name=btn_pattern)
                if loc.count() > 0:
                    btn_enviar = loc.first
                    break
            if btn_enviar is None:
                btn_enviar = page.get_by_text(btn_pattern).first

            btn_enviar.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            self.stdout.write('Clicando em "Receber por e-mail"...')

            pages_antes = list(ctx.pages)
            url_antes = page.url
            btn_enviar.click(timeout=10000)
            page.wait_for_timeout(4000)

            # Detecta se abriu nova aba ou navegou na mesma aba
            novas_abas = [p for p in ctx.pages if p not in pages_antes]
            if novas_abas:
                nova_aba = novas_abas[0]
                nova_aba.wait_for_load_state('load', timeout=30000)
                self.stdout.write(f'Nova aba detectada: {nova_aba.url}')
            elif page.url != url_antes:
                nova_aba = page
                self.stdout.write(f'Navegou na mesma aba: {nova_aba.url}')
            else:
                raise CommandError(
                    'Nenhuma ação detectada após clicar em "Receber por e-mail". '
                    'Verifique se o botão correto foi clicado.'
                )

            # ── Aguarda "CLIQUE AQUI PARA BAIXAR O ARQUIVO GERADO" ────────────
            self.stdout.write(f'Aguardando geração (até {options["timeout_geracao"]}s)...')
            dl_pattern = _re.compile(r'clique aqui para baixar|baixar arquivo csv', _re.IGNORECASE)
            deadline = time.time() + options['timeout_geracao']
            btn_download = None

            while time.time() < deadline:
                try:
                    loc = nova_aba.get_by_text(dl_pattern).first
                    if loc.count() > 0 and loc.is_visible(timeout=1000):
                        btn_download = loc
                        break
                except Exception:
                    pass
                self.stdout.write(f'  aguardando... ({int(deadline - time.time())}s restantes)')
                nova_aba.wait_for_timeout(5000)

            if not btn_download:
                raise CommandError(
                    f'Botão de download não apareceu em {options["timeout_geracao"]}s.'
                )

            self.stdout.write('Relatório pronto! Baixando...')

            # ── Baixa o arquivo ───────────────────────────────────────────────
            with nova_aba.expect_download(timeout=60000) as dl_info:
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
                page.locator(sel_ate).first.fill('01/01/3000')
                break
        else:
            self._preencher_data_por_label(page, 'Até', '01/01/3000')

        # ── Empreendimento ────────────────────────────────────────────────────
        self.stdout.write('Selecionando empreendimento Cota 365...')
        self._selecionar_empreendimento(page, 'Cota 365')

        # ── Situação da reserva ───────────────────────────────────────────────
        self.stdout.write('Configurando situação da reserva...')
        # Desmarca TODAS via JS (o form tem ~18 situações; enumerar seria frágil)
        desmarcadas_sit = page.evaluate('''() => {
            let n = 0;
            document.querySelectorAll('input[name="situacao[]"]').forEach(cb => {
                if (cb.checked) { cb.click(); n++; }
            });
            return n;
        }''')
        self.stdout.write(f'  {desmarcadas_sit} situações desmarcadas')
        page.wait_for_timeout(300)
        # Marca apenas "Vendida"
        self._set_checkbox_por_label(page, 'Vendida', True)
        page.wait_for_timeout(300)

        # ── Colunas de exibição ───────────────────────────────────────────────
        self.stdout.write('Configurando colunas...')
        # Descobre o name dos checkboxes de colunas e desmarca todos via JS
        col_names = page.evaluate('''() => {
            const names = new Set();
            document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                if (cb.name && cb.name !== 'situacao[]') names.add(cb.name);
            });
            return [...names];
        }''')
        self.stdout.write(f'  Checkbox names (não-situação): {col_names}')

        # Tenta desmarcar via JS com os nomes descobertos
        desmarcadas_col = page.evaluate('''(names) => {
            let n = 0;
            names.forEach(name => {
                document.querySelectorAll(`input[name="${name}"]`).forEach(cb => {
                    if (cb.checked) { cb.click(); n++; }
                });
            });
            return n;
        }''', col_names)
        self.stdout.write(f'  {desmarcadas_col} colunas desmarcadas')

        # Fallback: botão "Desmarcar todos" (último = seção de colunas)
        if desmarcadas_col == 0:
            btn_desmarcar_loc = page.get_by_text(_re.compile('desmarcar todos', _re.IGNORECASE))
            if btn_desmarcar_loc.count() > 0:
                btn_desmarcar_loc.last.click()
                page.wait_for_timeout(800)
                self.stdout.write('  "Desmarcar todos" clicado via botão')

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
        """Seleciona empreendimento pelo name do campo."""
        import re as _re

        # 1) Seletores CSS diretos pelo name/id
        for css in [
            'select[name="q[1|e.idempreendimento]"]',
            'select[name*="idempreendimento"]',
            'select[id*="empreendimento"]',
            'select[name*="empreendimento"]',
        ]:
            sel = page.locator(css)
            if sel.count() > 0:
                self.stdout.write(f'  Empreendimento via {css}')
                try:
                    sel.first.select_option(label=nome)
                except Exception:
                    sel.first.select_option(value='3')
                return

        # 2) Busca via label "Empreendimento"
        for lbl in page.locator('label').all():
            try:
                txt = lbl.inner_text(timeout=500).strip()
            except Exception:
                continue
            if _re.search(r'empreendimento', txt, _re.IGNORECASE):
                for_id = lbl.get_attribute('for')
                if for_id:
                    sel = page.locator(f'#{for_id}')
                    if sel.count() > 0:
                        self.stdout.write(f'  Empreendimento via label (for=#{for_id})')
                        try:
                            sel.first.select_option(label=nome)
                        except Exception:
                            sel.first.select_option(value='3')
                        return

        # 3) Diagnóstico: mostra todos os selects para depuração
        selects_info = page.evaluate('''() =>
            Array.from(document.querySelectorAll("select")).map(s => ({
                name: s.name, id: s.id,
                opts: Array.from(s.options).slice(0, 4).map(o => o.text.trim())
            }))
        ''')
        self.stdout.write(self.style.WARNING(
            f'  Select de empreendimento não encontrado.\n  Selects disponíveis: {selects_info}'
        ))
        input(f'  Selecione "{nome}" manualmente e pressione ENTER... ')

    def _set_checkbox_por_label(self, page, label_txt, checked: bool):
        """Marca/desmarca checkbox pelo texto do label."""

        def _apply(cb):
            if checked and not cb.is_checked():
                cb.check()
            elif not checked and cb.is_checked():
                cb.uncheck()

        # Estratégia 1: aria role + accessible name — funciona com IDs duplicados
        cb = page.get_by_role('checkbox', name=label_txt, exact=True)
        if cb.count() > 0:
            _apply(cb.first)
            return

        # Estratégia 2: label com texto exato → checkbox dentro ou via for
        for loc in [
            page.locator('label', has_text=label_txt),
            page.locator(f'label:has-text("{label_txt}")'),
        ]:
            if loc.count() > 0:
                lbl = loc.first
                cb = lbl.locator('input[type="checkbox"]')
                if cb.count() > 0:
                    _apply(cb.first)
                    return
                # label externo — usa .first para evitar strict mode em IDs duplicados
                for_id = lbl.get_attribute('for')
                if for_id:
                    cb = page.locator(f'#{for_id}').first
                    if cb.count() > 0:
                        _apply(cb)
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
