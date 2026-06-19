"""
Baixa o relatório de parcelas a receber (areceber.csv) do Sienge.

Fluxo:
  1. Abre Chrome real via CDP
  2. Navega para /sienge/8/index.html#/common/page/4855
  3. Preenche o formulário:
       - Modelo: Padrão
       - Empresas: 1 + Tab
       - Período de vencimento: 01/01/2000 → 31/12/3000
       - Centro de custo: 100 + Tab
       - Correção até: data de hoje (DD/MM/AAAA)
  4. Clica em "VISUALIZAR"
  5. Na nova aba, clica no ícone "Exportar dados"
  6. Move todas as colunas da esquerda para a direita
  7. Separador: Ponto e Vírgula (;)
  8. Clica OK e salva areceber.csv

Uso:
    python manage.py baixar_areceber_sienge
    python manage.py baixar_areceber_sienge --output="G:/Meu Drive/_intranet/cota365/areceber.csv"
"""

import subprocess
import time
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

DESTINO_PADRAO = r"G:\Meu Drive\_intranet\cota365\areceber.csv"
RELATORIO_URL  = 'https://cotaemp.sienge.com.br/sienge/8/index.html#/common/page/4855'


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Chrome não encontrado.')


class Command(BaseCommand):
    help = 'Baixa areceber.csv do relatório de contas a receber do Sienge.'

    def add_arguments(self, parser):
        parser.add_argument('--output', type=str, default=DESTINO_PADRAO)
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright
        import re as _re

        output_path = Path(options['output'])
        port        = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        profile_dir = options['profile_dir'] or str(
            Path(settings.BASE_DIR) / '.sienge_chrome_profile'
        )
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        hoje = date.today().strftime('%d/%m/%Y')

        with sync_playwright() as p:
            browser = self._connect_or_launch(p, chrome_path, profile_dir, port, RELATORIO_URL)
            ctx  = browser.contexts[0]
            page = next(
                (pg for pg in ctx.pages if 'sienge.com.br' in pg.url),
                ctx.pages[0],
            )

            try:
                page.wait_for_load_state('load', timeout=15000)
            except Exception:
                pass

            # Navega para o relatório
            self.stdout.write(f'Navegando para {RELATORIO_URL}...')
            page.goto(RELATORIO_URL, wait_until='networkidle', timeout=60000)
            page.wait_for_timeout(2000)

            # Detecta login e re-navega até o formulário aparecer
            while self._precisa_login(page):
                self.stdout.write(self.style.WARNING(
                    'Login necessário. Faça login no Sienge (clique em "ENTRAR COM SIENGE ID").'
                ))
                input('  Pressione ENTER após estar logado no Sienge... ')
                page.wait_for_timeout(2000)
                page.goto(RELATORIO_URL, wait_until='networkidle', timeout=60000)
                page.wait_for_timeout(2000)

            # Aguarda formulário aparecer (espera label ou input visível)
            self.stdout.write('Aguardando formulário carregar...')
            try:
                page.wait_for_selector('label, select, input[type="text"]',
                                       state='visible', timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(2000)

            # Diagnóstico completo da página
            frames_info = page.evaluate('''() => ({
                url: location.href,
                title: document.title,
                iframes: Array.from(document.querySelectorAll("iframe")).map(f => ({
                    src: f.src, id: f.id, name: f.name
                })),
                inputs_count: document.querySelectorAll("input").length,
                labels: Array.from(document.querySelectorAll("label"))
                    .map(l => l.innerText.trim()).filter(t => t).slice(0, 20),
                selects: Array.from(document.querySelectorAll("select"))
                    .map(s => ({id: s.id, name: s.name, opts: s.options.length})).slice(0, 10),
                body_snippet: document.body.innerText.slice(0, 500),
            })''')
            self.stdout.write(f'  Labels: {frames_info["labels"]}')
            self.stdout.write(f'  Selects: {frames_info["selects"]}')
            self.stdout.write(f'  Inputs: {frames_info["inputs_count"]}')
            self.stdout.write(f'  Body: {frames_info["body_snippet"][:300]}')

            # Detecta se o conteúdo está em um iframe
            frame = self._get_frame(page)
            self.stdout.write(f'  Frame usado: {frame.url}')

            # ── Preenche o formulário ──────────────────────────────────────────
            self._preencher_formulario(frame, hoje)

            # Fecha alertas/overlays
            page.evaluate('''() => {
                document.querySelectorAll(".alert .close, .modal .close, [data-dismiss]")
                    .forEach(b => b.click());
            }''')
            page.wait_for_timeout(300)

            # ── Clica em "VISUALIZAR" ──────────────────────────────────────────
            self.stdout.write('Clicando em VISUALIZAR...')
            url_antes = page.url

            try:
                with ctx.expect_page(timeout=20000) as nova_aba_info:
                    self._clicar_visualizar(page)
                nova_aba = nova_aba_info.value
                nova_aba.wait_for_load_state('load', timeout=30000)
                self.stdout.write(f'Nova aba: {nova_aba.url}')
            except Exception:
                page.wait_for_timeout(5000)
                novas = [pg for pg in ctx.pages if pg.url != url_antes and 'sienge' in pg.url]
                if novas:
                    nova_aba = novas[-1]
                    self.stdout.write(f'Nova aba detectada: {nova_aba.url}')
                else:
                    raise CommandError('VISUALIZAR não abriu nova aba.')

            # ── Clica em "Exportar dados" ──────────────────────────────────────
            self.stdout.write('Aguardando relatório carregar...')
            nova_aba.wait_for_timeout(3000)
            self._clicar_exportar(nova_aba)

            # ── Configura exportação ───────────────────────────────────────────
            self.stdout.write('Configurando exportação...')
            nova_aba.wait_for_timeout(2000)
            self._configurar_exportacao(nova_aba)

            # ── Clica OK e captura download ────────────────────────────────────
            self.stdout.write('Clicando OK e aguardando download...')
            with nova_aba.expect_download(timeout=120000) as dl_info:
                self._clicar_ok(nova_aba)

            download = dl_info.value
            download.save_as(str(output_path))
            self.stdout.write(self.style.SUCCESS(
                f'✓ areceber.csv salvo em: {output_path}  ({output_path.stat().st_size:,} bytes)'
            ))

    # ── Detecção de login ─────────────────────────────────────────────────────

    def _precisa_login(self, page):
        """Retorna True se a página exibir a tela de login do Sienge."""
        try:
            texto = page.evaluate('() => document.body.innerText')
            return any(ind in texto.lower() for ind in [
                'entrar com sienge id', 'bem-vindo!\ncota', 'sienge id'
            ])
        except Exception:
            return False

    # ── Detecção de frame ─────────────────────────────────────────────────────

    def _get_frame(self, page):
        """Retorna o frame correto — page direta ou o iframe com inputs."""
        # Se a própria página tem inputs, usa ela
        if page.locator('input').count() > 0:
            return page
        # Procura iframe com inputs
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                if frame.locator('input').count() > 0:
                    return frame
            except Exception:
                pass
        # Fallback: tenta o primeiro iframe encontrado
        iframes = page.locator('iframe')
        if iframes.count() > 0:
            frame = page.frame(url=iframes.first.get_attribute('src') or '')
            if frame:
                return frame
        return page

    # ── Preenchimento do formulário ───────────────────────────────────────────

    def _preencher_formulario(self, page, hoje):
        self.stdout.write('Preenchendo formulário...')

        # Diagnóstico: estrutura real da página logada
        diag = page.evaluate('''() => ({
            inputs: Array.from(document.querySelectorAll("input"))
                .filter(i => i.offsetParent !== null)
                .map(i => ({id: i.id, name: i.name, type: i.type, val: i.value,
                            placeholder: i.placeholder})).slice(0, 25),
            tds: Array.from(document.querySelectorAll("td"))
                .filter(td => td.offsetParent !== null && td.innerText.trim())
                .map(td => td.innerText.trim()).slice(0, 30),
        })''')
        self.stdout.write(f'  Inputs visíveis: {diag["inputs"]}')
        self.stdout.write(f'  TDs visíveis: {diag["tds"]}')

        # ── Modelo: "Padrão" (campo de texto com busca) ───────────────────────
        self.stdout.write('  Modelo → Padrão')
        self._preencher_sienge(page, 'Modelo', 'Padrão', tab=True)

        # ── Empresa: 1 + Tab ──────────────────────────────────────────────────
        self.stdout.write('  Empresa → 1 + Tab')
        self._preencher_sienge(page, 'Empresa', '1', tab=True)
        page.wait_for_timeout(800)

        # ── Período de vencimento: limpa e preenche as datas ──────────────────
        self.stdout.write('  Período de vencimento → 01/01/2000 e 31/12/3000')
        self._preencher_datas_periodo(page, 'vencimento', '01/01/2000', '31/12/3000')

        # ── Centro de custo: 100 + Tab ────────────────────────────────────────
        self.stdout.write('  Centro de custo → 100 + Tab')
        self._preencher_sienge(page, 'Centro de custo', '100', tab=True)
        page.wait_for_timeout(800)

        # ── Correção até: hoje ────────────────────────────────────────────────
        self.stdout.write(f'  Correção até → {hoje}')
        self._preencher_sienge(page, 'Correção até', hoje, tab=False)
        page.wait_for_timeout(300)

    def _preencher_sienge(self, page, label_txt, valor, tab=False):
        """Preenche campo do Sienge buscando pelo texto da célula <td> adjacente."""
        import re as _re
        resultado = page.evaluate('''([lbl, val, pressTab]) => {
            // Sienge usa <td> como label e o input fica no <td> seguinte
            const tds = Array.from(document.querySelectorAll("td, th, label, span"))
                .filter(el => el.offsetParent !== null);
            for (const td of tds) {
                if (!new RegExp(lbl.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&"), "i")
                    .test(td.innerText)) continue;
                // Próximo <td> ou elemento irmão com input
                const next = td.nextElementSibling || td.parentElement?.nextElementSibling;
                if (!next) continue;
                const inp = next.querySelector("input") ||
                            next.querySelector("select");
                if (!inp) continue;
                inp.focus();
                inp.value = val;
                ["input","change"].forEach(ev =>
                    inp.dispatchEvent(new Event(ev, {bubbles:true}))
                );
                if (pressTab) {
                    inp.dispatchEvent(new KeyboardEvent("keydown",
                        {key:"Tab", keyCode:9, bubbles:true}));
                }
                return {ok: true, id: inp.id, name: inp.name};
            }
            return {ok: false};
        }''', [label_txt, valor, tab])
        if resultado.get('ok'):
            self.stdout.write(f'    OK → {resultado}')
            if tab:
                page.wait_for_timeout(800)
        else:
            self.stdout.write(self.style.WARNING(f'    "{label_txt}" não encontrado'))
            # Fallback: Playwright press Tab nativo
            self._preencher_campo_por_label(page, label_txt, valor, pressionar_tab=tab)

    def _selecionar_opcao_por_label(self, page, label_txt, opcao_txt):
        parcial = ' '.join(opcao_txt.split()[-2:]).lower()
        encontrados = page.evaluate('''([labelBusca, opcaoExata, parcial]) => {
            const labels = Array.from(document.querySelectorAll("label"));
            let n = 0;
            labels.forEach(lbl => {
                if (!new RegExp(labelBusca, "i").test(lbl.textContent)) return;
                const sel = document.getElementById(lbl.htmlFor) ||
                            lbl.querySelector("select");
                if (!sel || sel.tagName !== "SELECT") return;
                let opt = Array.from(sel.options).find(o => o.text === opcaoExata);
                if (!opt) opt = Array.from(sel.options).find(o =>
                    o.text.toLowerCase().includes(parcial)
                );
                if (!opt) return;
                sel.value = opt.value;
                sel.dispatchEvent(new Event("change", {bubbles: true}));
                n++;
            });
            return n;
        }''', [label_txt, opcao_txt, parcial])
        if not encontrados:
            self.stdout.write(self.style.WARNING(f'    Select "{label_txt}" não encontrado'))

    def _preencher_campo_por_label(self, page, label_txt, valor, pressionar_tab=False):
        import re as _re
        # Tenta via label
        for lbl in page.locator('label').all():
            try:
                txt = lbl.inner_text(timeout=500).strip()
            except Exception:
                continue
            if _re.search(_re.escape(label_txt), txt, _re.IGNORECASE):
                for_id = lbl.get_attribute('for')
                inp = None
                if for_id:
                    loc = page.locator(f'#{for_id}')
                    if loc.count() > 0:
                        inp = loc.first
                if inp is None:
                    inp = lbl.locator('input').first if lbl.locator('input').count() > 0 else None
                if inp:
                    inp.triple_click()
                    inp.fill(valor)
                    if pressionar_tab:
                        inp.press('Tab')
                        page.wait_for_timeout(800)
                    return
        # Fallback: placeholder ou aria-label
        for attr in [f'[placeholder*="{label_txt}" i]', f'[aria-label*="{label_txt}" i]']:
            loc = page.locator(attr)
            if loc.count() > 0:
                loc.first.triple_click()
                loc.first.fill(valor)
                if pressionar_tab:
                    loc.first.press('Tab')
                    page.wait_for_timeout(800)
                return
        self.stdout.write(self.style.WARNING(f'    Campo "{label_txt}" não encontrado'))

    def _preencher_datas_periodo(self, page, label_hint, data_ini, data_fim):
        import re as _re
        # Procura por um par de inputs de data próximos ao label com o hint
        resultado = page.evaluate('''([hint, ini, fim]) => {
            const labels = Array.from(document.querySelectorAll("label"));
            for (const lbl of labels) {
                if (!new RegExp(hint, "i").test(lbl.textContent)) continue;
                // Procura inputs de data no mesmo container pai
                let container = lbl.parentElement;
                for (let i = 0; i < 4; i++) {
                    const inputs = Array.from(
                        container.querySelectorAll("input[type=text], input[type=date]")
                    ).filter(inp => inp.offsetParent !== null);
                    if (inputs.length >= 2) {
                        function set(el, val) {
                            el.value = val;
                            ["input","change","blur"].forEach(ev =>
                                el.dispatchEvent(new Event(ev, {bubbles: true}))
                            );
                        }
                        set(inputs[0], ini);
                        set(inputs[1], fim);
                        return {ok: true, de: inputs[0].id||inputs[0].name,
                                ate: inputs[1].id||inputs[1].name};
                    }
                    container = container.parentElement;
                    if (!container) break;
                }
            }
            return {ok: false};
        }''', [label_hint, data_ini, data_fim])
        self.stdout.write(f'    Datas período: {resultado}')

    def _clicar_visualizar(self, page):
        import re as _re
        for seletor in [
            'button:has-text("VISUALIZAR")',
            'input[value*="VISUALIZAR" i]',
            'button:has-text("Visualizar")',
            'a:has-text("VISUALIZAR")',
        ]:
            loc = page.locator(seletor)
            if loc.count() > 0:
                loc.first.click(force=True, timeout=10000)
                return
        btn = page.get_by_text(_re.compile(r'visualizar', _re.IGNORECASE)).first
        btn.click(force=True, timeout=10000)

    def _clicar_exportar(self, page):
        import re as _re
        self.stdout.write('Clicando em Exportar dados...')

        # Diagnóstico: botões visíveis
        btns = page.evaluate('''() =>
            Array.from(document.querySelectorAll("button, a, [title], [class*=export], [class*=Export]"))
            .filter(el => el.offsetParent !== null)
            .map(el => ({tag: el.tagName, text: el.innerText?.trim().slice(0,40),
                         title: el.title, cls: el.className.slice(0,60)}))
            .slice(0, 20)
        ''')
        self.stdout.write(f'  Botões/links visíveis: {btns}')

        for seletor in [
            '[title*="Exportar" i]',
            '[title*="Export" i]',
            'button[class*="export" i]',
            'a[class*="export" i]',
            '.export-button',
            '[aria-label*="Exportar" i]',
            '[aria-label*="Export" i]',
        ]:
            loc = page.locator(seletor)
            if loc.count() > 0:
                self.stdout.write(f'  Exportar via {seletor}')
                loc.first.click(force=True, timeout=10000)
                page.wait_for_timeout(1500)
                return

        # Fallback texto
        loc = page.get_by_text(_re.compile(r'exportar', _re.IGNORECASE))
        if loc.count() > 0:
            loc.first.click(force=True, timeout=10000)
            page.wait_for_timeout(1500)
            return

        raise CommandError('Ícone "Exportar dados" não encontrado. Verifique os botões no log.')

    def _configurar_exportacao(self, page):
        self.stdout.write('  Selecionando todas as colunas...')

        # Move todas as colunas da esquerda para direita
        # Tenta botão ">>" (mover tudo)
        for seletor in ['button:has-text(">>")', 'input[value=">>"]',
                        '[title*="Mover todos" i]', '[title*="All" i]',
                        'button:has-text("Selecionar todos")', '.move-all']:
            loc = page.locator(seletor)
            if loc.count() > 0:
                loc.first.click(timeout=5000)
                page.wait_for_timeout(500)
                self.stdout.write(f'  Todas colunas movidas via {seletor}')
                break
        else:
            # Seleciona todos na lista esquerda e move
            page.evaluate('''() => {
                const selects = Array.from(document.querySelectorAll("select"))
                    .filter(s => s.offsetParent !== null && s.multiple);
                if (selects.length > 0) {
                    Array.from(selects[0].options).forEach(o => o.selected = true);
                }
            }''')
            for seletor in ['button:has-text(">")', 'input[value=">"]']:
                loc = page.locator(seletor)
                if loc.count() > 0:
                    loc.first.click(timeout=5000)
                    page.wait_for_timeout(500)
                    break

        # Separador: Ponto e Vírgula
        self.stdout.write('  Separador → Ponto e Vírgula (;)')
        sep_selecionado = page.evaluate('''() => {
            const labels = Array.from(document.querySelectorAll("label, span, div"));
            for (const el of labels) {
                if (!/separador/i.test(el.textContent)) continue;
                const radios = el.closest("form,div,section")
                    ?.querySelectorAll("input[type=radio]") || [];
                for (const r of radios) {
                    const lbl = document.querySelector(`label[for="${r.id}"]`);
                    if (lbl && /ponto.v[íi]rgula|semicol|;/i.test(lbl.textContent)) {
                        r.checked = true;
                        r.dispatchEvent(new Event("change", {bubbles:true}));
                        return lbl.textContent.trim();
                    }
                }
            }
            // Fallback: procura qualquer radio com ; no label
            for (const r of document.querySelectorAll("input[type=radio]")) {
                const lbl = document.querySelector(`label[for="${r.id}"]`);
                if (lbl && /;|ponto.v[íi]rgula|semicol/i.test(lbl.textContent)) {
                    r.checked = true;
                    r.dispatchEvent(new Event("change", {bubbles:true}));
                    return lbl.textContent.trim();
                }
            }
            return null;
        }''')
        self.stdout.write(f'  Separador selecionado: {sep_selecionado}')

    def _clicar_ok(self, page):
        import re as _re
        for seletor in ['button:has-text("OK")', 'input[value="OK"]',
                        'button:has-text("Ok")', '.btn-primary:has-text("OK")']:
            loc = page.locator(seletor)
            if loc.count() > 0:
                loc.first.click(force=True, timeout=10000)
                return
        page.get_by_text(_re.compile(r'^ok$', _re.IGNORECASE)).first.click(
            force=True, timeout=10000
        )

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
