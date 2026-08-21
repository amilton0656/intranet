"""
Baixa o PDF "Unidades disponíveis" via mapa de Disponibilidade do CV CRM.
Serve para qualquer empreendimento — Bliss Living tem uma única tabela (sem
--nome-tabela ele acha a única linha disponível); o Cota 365 tem várias
tabelas na mesma página, então precisa de --nome-tabela pra escolher qual.

Fluxo:
  1. Abre Chrome real via CDP (evita Cloudflare Turnstile)
  2. Navega direto para /gestor/comercial/mapadisponibilidade/<id>
  3. Na seção "Tabelas de preço disponíveis", acha a linha certa (por nome,
     se --nome-tabela for informado) → botão de opções (⋮)
  4. Clica em "PDF Unidades disponíveis" → captura o download

Uso:
    python manage.py baixar_tabela_disponibilidade_cvcrm
        (Bliss Living, id=2, padrão)

    python manage.py baixar_tabela_disponibilidade_cvcrm --empreendimento-id=3 \\
        --nome-tabela="Tabela Curta" --output="G:/Meu Drive/_intranet/tabelas/COTA 365 - Tabela Curta.pdf"

ATENÇÃO: seletores ajustados a partir de testes ao vivo, mas o passo do menu
de opções (⋮) ainda tem fallback manual — se o script não achar o botão, ele
avisa e pede pra você clicar manualmente, sem travar a execução.
"""

import re as _re
import subprocess
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

DESTINO_PADRAO       = r"G:\Meu Drive\_intranet\tabelas\BLISS LIVING - bancaria.pdf"
BASE_URL             = 'https://cota.cvcrm.com.br'
EMPREENDIMENTO_BLISS = 2


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Chrome não encontrado. Use --chrome-path para indicar o executável.')


class Command(BaseCommand):
    help = 'Baixa o PDF "Unidades disponíveis" do mapa de Disponibilidade do CV CRM.'

    def add_arguments(self, parser):
        parser.add_argument('--empreendimento-id', type=int, default=EMPREENDIMENTO_BLISS,
                            help=f'ID do empreendimento na URL do mapa (padrão: {EMPREENDIMENTO_BLISS} = Bliss Living)')
        parser.add_argument('--nome-tabela', type=str, default=None,
                            help='Nome (ou trecho do nome) da tabela a baixar, quando a página tem '
                                 'mais de uma (ex: "Tabela Curta"). Sem isso, tenta achar uma tabela '
                                 'com nome de mês/ano (padrão do Bliss) e cai para a única linha visível.')
        parser.add_argument('--output', type=str, default=DESTINO_PADRAO,
                            help=f'Caminho de destino (padrão: {DESTINO_PADRAO})')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        empreendimento_id = options['empreendimento_id']
        mapa_url    = f'{BASE_URL}/gestor/comercial/mapadisponibilidade/{empreendimento_id}'
        output_path = Path(options['output'])
        port        = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        # Mesmo perfil dos outros comandos CV CRM — reaproveita a sessão já logada.
        profile_dir = options['profile_dir'] or str(
            Path(settings.BASE_DIR) / '.cvcrm_chrome_profile'
        )
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            browser = self._connect_or_launch(p, chrome_path, profile_dir, port, mapa_url)
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

            # Sempre navega para a URL (garante estado limpo mesmo se a sessão já
            # estava aberta em outra página)
            self.stdout.write(f'Navegando para {mapa_url}...')
            page.goto(mapa_url, wait_until='load', timeout=30000)
            page.wait_for_timeout(1500)

            # Verifica login de novo (a navegação pode ter redirecionado pro login)
            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Sessão expirada. Faça login manualmente na janela do Chrome.'
                ))
                input('Pressione ENTER após estar logado... ')
                page.goto(mapa_url, wait_until='load', timeout=30000)
                page.wait_for_timeout(1500)

            # ── Expande "Abrir mais informações", se existir nessa tela ────────
            self._abrir_mais_informacoes(page)

            # ── Abre o menu (⋮) e clica em "PDF Unidades disponíveis" ──────────
            # IMPORTANTE: a captura do download (expect_download) começa ANTES de
            # qualquer clique — automático ou manual. Dropdowns fecham sozinhos
            # depois de um tempo, então tentar clicar "depois" de uma pausa manual
            # (input()) frequentemente falha porque o menu já fechou. Capturando
            # o download antes, o Playwright pega o arquivo não importa quem
            # clicou nem quando.
            self.stdout.write('Abrindo opções de "Tabelas de preço disponíveis"...')
            with page.expect_download(timeout=120000) as dl_info:
                achou_linha = self._abrir_menu_opcoes_tabela(page, options['nome_tabela'])
                clicou_pdf = False
                if achou_linha:
                    page.wait_for_timeout(500)
                    self.stdout.write('Clicando em "PDF Unidades disponíveis"...')
                    try:
                        self._clicar_por_texto(page, r'pdf\s+unidades\s+dispon[íi]veis', timeout=8000)
                        clicou_pdf = True
                    except CommandError:
                        clicou_pdf = False

                if not clicou_pdf:
                    self.stdout.write(self.style.WARNING(
                        '  Não consegui automatizar até o fim. No Chrome: abra o menu (⋮) '
                        'da tabela certa e clique em "PDF Unidades disponíveis". '
                        'O download será capturado assim que você clicar.'
                    ))
                    input('  Pressione ENTER só depois de clicar (o script já está esperando o download)... ')

            download = dl_info.value
            download.save_as(str(output_path))
            self.stdout.write(self.style.SUCCESS(
                f'✓ PDF salvo em: {output_path}  ({output_path.stat().st_size:,} bytes)'
            ))

    # ── Helpers de navegação ─────────────────────────────────────────────────

    def _clicar_por_texto(self, page, padrao_regex, timeout=10000):
        """Clica no primeiro elemento visível cujo texto bate com o regex (case-insensitive).
        Espera de verdade o elemento aparecer (auto-wait do Playwright) em vez de checar
        count() na hora — count() é instantâneo e não espera a página renderizar."""
        loc = page.get_by_text(_re.compile(padrao_regex, _re.IGNORECASE))
        try:
            loc.first.wait_for(state='visible', timeout=timeout)
        except Exception:
            raise CommandError(
                f'Nenhum elemento visível encontrado com texto "{padrao_regex}" '
                f'após {timeout}ms. A tela pode ter mudado — verifique manualmente no Chrome.'
            )
        loc.first.click(timeout=5000)

    def _abrir_mais_informacoes(self, page):
        """Clica em "Abrir mais informações" se existir na página (em algumas
        telas isso é necessário pra revelar a seção "Tabelas de preço
        disponíveis"). Não falha se não encontrar — a seção pode já vir
        expandida (ex: no Bliss, que tem só uma tabela)."""
        try:
            loc = page.get_by_text(_re.compile(r'abrir\s+mais\s+informa[çc][õo]es', _re.IGNORECASE))
            loc.first.wait_for(state='visible', timeout=5000)
            loc.first.click(timeout=5000)
            self.stdout.write('  Cliquei em "Abrir mais informações".')
            page.wait_for_timeout(800)
        except Exception:
            pass

    def _abrir_menu_opcoes_tabela(self, page, nome_tabela=None):
        """Encontra a linha da tabela de preço e clica no botão de opções (⋮)
        dela. Retorna True se conseguiu clicar em algo, False se não achou
        nada automaticamente (o chamador decide o que fazer — não pausa aqui,
        pois pausar entre "abrir o menu" e "clicar no PDF" faz o dropdown
        fechar sozinho antes do próximo clique).

        Se --nome-tabela for informado, ele é OBRIGATÓRIO — se não achar
        exatamente esse texto na página, retorna False em vez de cair num
        fallback genérico (que pegaria a linha errada em silêncio quando há
        várias tabelas, como no Cota 365).

        Ordem de tentativas quando --nome-tabela NÃO é informado:
          1. Padrão "Tabela <mês>/<ano>" (caso do Bliss, que só tem uma)
          2. Título da seção "Tabelas de preço disponíveis" (só serve quando
             há uma única tabela na página)
        """
        if nome_tabela:
            candidatos = [(f'nome "{nome_tabela}"', _re.compile(_re.escape(nome_tabela), _re.IGNORECASE))]
        else:
            candidatos = [
                ('padrão "Tabela mês/ano"', _re.compile(r'tabela\s+\w+/\d{4}', _re.IGNORECASE)),
                ('título da seção', _re.compile(r'tabelas?\s+de\s+pre[çc]o\s+dispon[íi]ve', _re.IGNORECASE)),
            ]

        linha_loc = None
        for descricao, padrao in candidatos:
            tentativa = page.get_by_text(padrao)
            try:
                tentativa.first.wait_for(state='visible', timeout=10000)
                linha_loc = tentativa
                self.stdout.write(f'  Linha encontrada via {descricao}.')
                break
            except Exception:
                continue

        if linha_loc is None:
            self.stdout.write(self.style.WARNING(
                '  Não encontrei a linha da tabela automaticamente.'
            ))
            return False

        # Seletores conhecidos de botão de menu (⋮), tentados em containers
        # cada vez maiores a partir da linha.
        seletores_conhecidos = [
            'button[aria-label*="ção" i]',
            'button[aria-label*="option" i]',
            '.dropdown-toggle',
            'button:has-text("⋮")',
            'button:has-text("...")',
            '[data-bs-toggle="dropdown"]',
            'i[class*="ellipsis" i]',
            'i[class*="dots" i]',
            'i[class*="vertical" i]',
            'i[class*="more" i]',
            'i[class*="kebab" i]',
            '.material-icons',
            'svg',
        ]

        for niveis in range(0, 6):
            container = (
                linha_loc.first if niveis == 0
                else linha_loc.first.locator('xpath=' + '/'.join(['..'] * niveis))
            )

            for seletor in seletores_conhecidos:
                try:
                    btn = container.locator(seletor)
                    if btn.count() > 0 and btn.first.is_visible(timeout=500):
                        btn.first.click(timeout=5000)
                        return True
                except Exception:
                    continue

            # Estratégia genérica: clica no ÚLTIMO elemento clicável da linha
            # (padrão comum: nome / data / ... / botão de opções no final).
            try:
                clicaveis = container.locator('button, a, [role="button"]')
                n = clicaveis.count()
                if n > 0:
                    ultimo = clicaveis.nth(n - 1)
                    if ultimo.is_visible(timeout=500):
                        ultimo.click(timeout=5000)
                        return True
            except Exception:
                pass

        self.stdout.write(self.style.WARNING(
            '  Não encontrei automaticamente o botão de opções (⋮) da tabela.'
        ))
        return False

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
