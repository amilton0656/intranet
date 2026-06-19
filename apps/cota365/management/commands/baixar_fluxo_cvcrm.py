"""
Baixa o relatório de fluxo mensal (fluxo.csv) do CV CRM.

Fluxo:
  1. Abre Chrome real via CDP (evita Cloudflare Turnstile)
  2. Navega para /gestor/relatorios/fluxo_mensal
  3. Preenche o formulário:
       - Empreendimento: Cota 365
       - Situação: Vendida (checkbox)
       - Tipo de período (Data Cadastro): Período definido pelo usuário
       - De: 01/01/2000 / Até: 31/12/3000
  4. Clica em "Gerar CSV" e captura o download

Uso:
    python manage.py baixar_fluxo_cvcrm
    python manage.py baixar_fluxo_cvcrm --output="G:/Meu Drive/_intranet/cota365/fluxo.csv"
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

DESTINO_PADRAO = r"G:\Meu Drive\_intranet\cota365\fluxo.csv"
BASE_URL       = 'https://cota.cvcrm.com.br'
RELATORIO_URL  = f'{BASE_URL}/gestor/relatorios/fluxo_mensal'


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Chrome não encontrado. Use --chrome-path para indicar o executável.')


class Command(BaseCommand):
    help = 'Baixa fluxo.csv do relatório de fluxo mensal do CV CRM.'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=DESTINO_PADRAO,
                            help=f'Caminho de destino (padrão: {DESTINO_PADRAO})')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        output_path = Path(options['output'])
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

            # Verifica login novamente
            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Sessão expirada. Faça login manualmente na janela do Chrome.'
                ))
                input('Pressione ENTER após estar logado... ')
                page.goto(RELATORIO_URL, wait_until='load', timeout=30000)
                page.wait_for_timeout(2000)

            # ── Preenche o formulário ──────────────────────────────────────────
            self._preencher_formulario(page)

            # Fecha notificações que possam sobrepor o botão
            page.evaluate('''() => {
                document.querySelectorAll(".alert .close, .alert [data-dismiss], .close")
                    .forEach(b => b.click());
            }''')
            page.wait_for_timeout(300)

            # ── Clica em "Gerar CSV" e captura o download ─────────────────────
            self.stdout.write('Clicando em "Gerar CSV"...')
            import re as _re

            btn = None
            for css in ['#gerar_csv', '[id*="gerar_csv"]', 'input[value*="CSV" i]',
                        'button:has-text("CSV")', 'a:has-text("CSV")']:
                loc = page.locator(css)
                if loc.count() > 0:
                    btn = loc.first
                    self.stdout.write(f'  Botão encontrado via {css}')
                    break
            if btn is None:
                btn = page.get_by_text(_re.compile(r'gerar\s+csv', _re.IGNORECASE)).first
                self.stdout.write('  Botão encontrado via texto "Gerar CSV"')

            try:
                with page.expect_download(timeout=120000) as dl_info:
                    btn.click(force=True, timeout=10000)
                download = dl_info.value
                download.save_as(str(output_path))
                self.stdout.write(self.style.SUCCESS(
                    f'✓ fluxo.csv salvo em: {output_path}  ({output_path.stat().st_size:,} bytes)'
                ))
            except Exception as e:
                # Botão pode abrir nova aba em vez de download direto
                self.stdout.write(self.style.WARNING(f'  Download direto falhou ({e}), tentando nova aba...'))
                url_antes = page.url
                try:
                    with ctx.expect_page(timeout=12000) as nova_aba_info:
                        btn.click(force=True, timeout=10000)
                    nova_aba = nova_aba_info.value
                    nova_aba.wait_for_load_state('load', timeout=30000)
                    self.stdout.write(f'  Nova aba: {nova_aba.url}')
                    with nova_aba.expect_download(timeout=120000) as dl_info:
                        nova_aba.get_by_text(
                            _re.compile(r'clique aqui para baixar|baixar arquivo', _re.IGNORECASE)
                        ).first.click(timeout=10000)
                    download = dl_info.value
                    download.save_as(str(output_path))
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ fluxo.csv salvo em: {output_path}  ({output_path.stat().st_size:,} bytes)'
                    ))
                except Exception as e2:
                    raise CommandError(f'Não foi possível baixar o arquivo: {e2}')

    def _preencher_formulario(self, page):
        # ── Empreendimento ────────────────────────────────────────────────────
        self.stdout.write('Selecionando empreendimento Cota 365...')
        self._selecionar_empreendimento(page, 'Cota 365')

        # ── Situação: marca "Vendida" ─────────────────────────────────────────
        self.stdout.write('Marcando situação Vendida...')
        desmarcadas = page.evaluate('''() => {
            let n = 0;
            document.querySelectorAll('input[name="situacao[]"]').forEach(cb => {
                if (cb.checked) { cb.click(); n++; }
            });
            return n;
        }''')
        self.stdout.write(f'  {desmarcadas} situações desmarcadas')
        page.wait_for_timeout(300)
        self._set_checkbox_por_label(page, 'Vendida', True)
        page.wait_for_timeout(300)

        # ── Tipo de período (Data Cadastro) → Período definido pelo usuário ───
        self.stdout.write('Configurando tipo de período...')
        self._selecionar_opcao_por_label(page, 'Data Cadastro', 'Período definido pelo usuário')
        self._selecionar_opcao_por_label(page, 'Data de cadastro', 'Período definido pelo usuário')
        page.wait_for_timeout(600)

        # ── Datas ─────────────────────────────────────────────────────────────
        self.stdout.write('Preenchendo datas...')

        # Diagnóstico: todos os inputs de texto visíveis
        inputs_vis = page.evaluate('''() =>
            Array.from(document.querySelectorAll('input[type="text"], input[type="date"]'))
            .filter(i => i.offsetParent !== null)
            .map(i => ({name: i.name, id: i.id, val: i.value}))
        ''')
        self.stdout.write(f'  Inputs visíveis: {inputs_vis}')

        # Tenta preencher por IDs conhecidos (form_de/form_ate) ou pelos dois
        # primeiros inputs de texto visíveis como fallback
        resultado = page.evaluate('''([de, ate]) => {
            function set(el, val) {
                el.value = val;
                ["input","change","blur"].forEach(ev =>
                    el.dispatchEvent(new Event(ev, {bubbles:true}))
                );
            }
            // Tenta IDs diretos
            const elDe  = document.getElementById("form_de");
            const elAte = document.getElementById("form_ate");
            if (elDe && elAte) {
                set(elDe, de); set(elAte, ate);
                return {via: "id", de: "form_de", ate: "form_ate"};
            }
            // Fallback: dois primeiros inputs de texto visíveis
            const vis = Array.from(
                document.querySelectorAll('input[type="text"], input[type="date"]')
            ).filter(i => i.offsetParent !== null);
            if (vis.length >= 2) {
                set(vis[0], de); set(vis[1], ate);
                return {via: "fallback", de: vis[0].id||vis[0].name, ate: vis[1].id||vis[1].name};
            }
            return {via: "falhou", count: vis.length};
        }''', ['01/01/2000', '31/12/3000'])
        self.stdout.write(f'  Resultado datas: {resultado}')

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _selecionar_empreendimento(self, page, nome):
        import re as _re
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

        self.stdout.write(self.style.WARNING(f'  Empreendimento não encontrado, selecione manualmente.'))
        input(f'  Selecione "{nome}" e pressione ENTER... ')

    def _selecionar_opcao_por_label(self, page, label_txt, opcao_txt):
        parcial = ' '.join(opcao_txt.split()[-3:]).lower()
        encontrados = page.evaluate('''([labelBusca, opcaoExata, parcial]) => {
            const labels = Array.from(document.querySelectorAll('label'));
            let n = 0;
            labels.forEach(lbl => {
                if (!new RegExp(labelBusca, 'i').test(lbl.textContent)) return;
                const sel = document.getElementById(lbl.htmlFor);
                if (!sel || sel.tagName !== 'SELECT') return;
                let opt = Array.from(sel.options).find(o => o.text === opcaoExata);
                if (!opt) opt = Array.from(sel.options).find(o =>
                    o.text.toLowerCase().includes(parcial)
                );
                if (!opt) return;
                sel.value = opt.value;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
                n++;
            });
            return n;
        }''', [label_txt, opcao_txt, parcial])

        if encontrados:
            self.stdout.write(f'  "{label_txt}" ({encontrados}x) → "{opcao_txt}"')
        else:
            self.stdout.write(self.style.WARNING(f'  Select "{label_txt}" não encontrado'))

    def _set_checkbox_por_label(self, page, label_txt, checked: bool):
        def _apply(cb):
            if checked and not cb.is_checked():
                cb.check()
            elif not checked and cb.is_checked():
                cb.uncheck()

        cb = page.get_by_role('checkbox', name=label_txt, exact=True)
        if cb.count() > 0:
            _apply(cb.first)
            return

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
