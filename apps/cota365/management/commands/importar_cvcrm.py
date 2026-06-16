"""
Importa dados de Unidades e Espaços Complementares do CV CRM para uma planilha Excel.

O login no CV CRM usa Cloudflare Turnstile, que bloqueia navegadores controlados
por automação (mesmo em modo visível). Por isso este comando abre o Chrome REAL
da máquina (não o Chromium do Playwright) e pede que você faça login manualmente
na primeira vez; depois disso a sessão fica salva em --profile-dir e os próximos
usos pulam o login enquanto a sessão do CV CRM continuar válida.

Uso:
    python manage.py importar_cvcrm
    python manage.py importar_cvcrm --empreendimento=3
    python manage.py importar_cvcrm --output=C:/caminho/saida.xlsx
"""

import re
import subprocess
import time
from pathlib import Path

import lxml.html
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

PRINCIPAL_HEADER = [
    'Nome', 'Tipologia', 'Tipo', 'Número de depósitos', 'Vagas de garagem',
    'Área privativa m2', 'Área comum', 'Área total', 'Fração Ideal',
]
COMPLEMENTARES_HEADER = [
    'Nome', 'Descrição do andar', 'Área (m2)', 'Área comum', 'Valor', 'Fração Ideal',
]


def to_float(value):
    """Números do export em CSV: ponto decimal, vírgula como milhar (ex.: 908,418.57)."""
    value = (value or '').strip()
    if not value:
        return None
    try:
        return float(value.replace(',', ''))
    except ValueError:
        return value


def to_float_br(value):
    """Números dos formulários HTML do CV CRM: vírgula decimal (ex.: 14,780 = 14.78)."""
    value = (value or '').strip()
    if not value:
        return None
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        return value


def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Não encontrei o Chrome instalado. Use --chrome-path para indicar o executável.')


class Command(BaseCommand):
    help = 'Importa Unidades e Espaços Complementares do CV CRM para um Excel (abas Principal e Complementares).'

    def add_arguments(self, parser):
        parser.add_argument('--empreendimento', type=int, default=3,
                             help='ID do empreendimento no CV CRM (padrão: 3 = Cota 365)')
        parser.add_argument('--output', type=str, default=None,
                             help='Caminho do arquivo Excel de saída')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None,
                             help='Pasta de perfil do Chrome usada para manter a sessão logada entre execuções')

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        emp_id = options['empreendimento']
        port = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        profile_dir = options['profile_dir'] or str(Path(settings.BASE_DIR) / '.cvcrm_chrome_profile')
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        base = 'https://cota.cvcrm.com.br'
        target_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/administrar#unidades'

        with sync_playwright() as p:
            browser = self._connect_or_launch(p, chrome_path, profile_dir, port, target_url)
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if 'cvcrm.com.br' in pg.url), ctx.pages[0])

            if page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Faça login manualmente na janela do Chrome (e-mail, senha e o desafio de segurança).'
                ))
                input('Pressione ENTER aqui depois de estar logado e na tela do empreendimento... ')

            if 'administrar' not in page.url:
                page.goto(target_url, wait_until='load', timeout=60000)
                page.wait_for_timeout(2000)

            self.stdout.write('Baixando export de Unidades...')
            principal_rows, lookup_sample_id = self._build_principal(page, base, emp_id)
            self.stdout.write(self.style.SUCCESS(f'  {len(principal_rows)} unidades.'))

            self.stdout.write('Coletando Espaços Complementares (pode levar alguns minutos)...')
            complementares_rows = self._build_complementares(page, base, emp_id)
            self.stdout.write(self.style.SUCCESS(f'  {len(complementares_rows)} espaços complementares.'))

            output_path = options['output'] or str(Path(settings.BASE_DIR) / 'cvcrm_importado.xlsx')
            self._salvar_excel(principal_rows, complementares_rows, output_path)
            self.stdout.write(self.style.SUCCESS(f'Planilha salva em: {output_path}'))

    def _connect_or_launch(self, p, chrome_path, profile_dir, port, target_url):
        try:
            return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
        except Exception:
            subprocess.Popen([
                chrome_path,
                f'--remote-debugging-port={port}',
                f'--user-data-dir={profile_dir}',
                target_url,
            ])
            for _ in range(15):
                time.sleep(1)
                try:
                    return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')
                except Exception:
                    continue
            raise CommandError('Não consegui conectar ao Chrome via debugging port.')

    def _build_principal(self, page, base, emp_id):
        download_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/exportar_unidades_download'
        resp = page.request.get(download_url)
        if resp.status != 200:
            raise CommandError(f'Falha ao baixar export de unidades (status {resp.status}).')
        text = resp.body().decode('utf-8-sig')

        lines = text.splitlines()
        header_idx = next(i for i, l in enumerate(lines) if 'ID Unidade' in l)
        header_fields = lines[header_idx].count(';') + 1

        data_lines = []
        for line in lines[header_idx + 1:]:
            if line.count(';') + 1 < header_fields:
                break
            data_lines.append(line)

        import csv
        reader = csv.DictReader([lines[header_idx]] + data_lines, delimiter=';')
        rows = list(reader)
        if not rows:
            return [], None

        sample_unit_id = rows[0]['ID Unidade']
        editar_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/unidades/{sample_unit_id}/editar'
        resp2 = page.request.get(editar_url)
        tree = lxml.html.fromstring(resp2.text())
        tipologia_map = self._select_options_map(tree, 'idtipologia')
        tipo_map = self._select_options_map(tree, 'idtipo')

        principal_rows = []
        for row in rows:
            principal_rows.append([
                row.get('Unidade', ''),
                tipologia_map.get(row.get('ID Tipologia', ''), row.get('ID Tipologia', '')),
                tipo_map.get(row.get('ID Tipo', ''), row.get('ID Tipo', '')),
                row.get('Quantidade depósito', ''),
                row.get('Vagas de garagem', ''),
                to_float(row.get('Área privativa')),
                to_float(row.get('Área comum')),
                to_float(row.get('Área total')),
                to_float(row.get('Fração Ideal')),
            ])
        return principal_rows, sample_unit_id

    def _select_options_map(self, tree, field_id):
        result = {}
        els = tree.get_element_by_id(field_id, None)
        if els is None:
            return result
        for opt in els.xpath('.//option'):
            val = opt.get('value')
            if val:
                result[val] = (opt.text or '').strip()
        return result

    def _build_complementares(self, page, base, emp_id):
        list_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/espacoscomplementares'
        resp = page.request.get(list_url)
        ids = sorted(set(int(m) for m in re.findall(r'espacoscomplementares/(\d+)/opcoes', resp.text())))

        rows = []
        for i, esp_id in enumerate(ids, 1):
            editar_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/espacoscomplementares/{esp_id}/editar'
            r = page.request.get(editar_url)
            if r.status != 200:
                self.stdout.write(self.style.WARNING(f'  Falhou espaço {esp_id} (status {r.status}), pulando.'))
                continue
            tree = lxml.html.fromstring(r.text())

            def val(field_id):
                el = tree.get_element_by_id(field_id, None)
                return el.get('value', '') if el is not None else ''

            def textarea_val(field_id):
                el = tree.get_element_by_id(field_id, None)
                return (el.text_content() or '').strip() if el is not None else ''

            rows.append([
                val('nome'),
                textarea_val('andar_descricao'),
                to_float_br(val('area')),
                to_float_br(val('area_comum')),
                to_float_br(val('valor')),
                to_float_br(val('fracao_ideal')),
            ])
            if i % 20 == 0 or i == len(ids):
                self.stdout.write(f'  {i}/{len(ids)} processados...')
        return rows

    def _salvar_excel(self, principal_rows, complementares_rows, output_path):
        from openpyxl import Workbook

        wb = Workbook()
        ws1 = wb.active
        ws1.title = 'Principal'
        ws1.append(PRINCIPAL_HEADER)
        for r in principal_rows:
            ws1.append(r)

        ws2 = wb.create_sheet('Complementares')
        ws2.append(COMPLEMENTARES_HEADER)
        for r in complementares_rows:
            ws2.append(r)

        wb.save(output_path)
