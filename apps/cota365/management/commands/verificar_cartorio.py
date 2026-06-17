"""
Verifica se os dados das Unidades e Espaços Complementares no CV CRM
estão corretos em relação ao cartório (cartorio.xlsx).

Usa a mesma conexão CDP do importar_cvcrm: conecta ao Chrome já aberto com
--remote-debugging-port=9222, ou abre um novo pedindo login manual.

Uso:
    python manage.py verificar_cartorio
    python manage.py verificar_cartorio --cartorio=C:/caminho/cartorio.xlsx
    python manage.py verificar_cartorio --so-divergencias
"""

import csv
import re
import subprocess
import time
from pathlib import Path

import lxml.html
import openpyxl
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

TOL = 0.005  # tolerância ±0.005 para comparação de áreas e fração ideal


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def find_chrome():
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    raise CommandError('Chrome não encontrado. Use --chrome-path para indicar o executável.')


def to_float_csv(value):
    """Converte float do CSV de export (formato US: vírgula = milhar)."""
    value = (value or '').strip()
    if not value:
        return None
    try:
        return float(value.replace(',', ''))
    except ValueError:
        return None


def to_float_br(value):
    """Converte float de formulário HTML CV CRM (formato BR: vírgula = decimal)."""
    value = (value or '').strip()
    if not value:
        return None
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        return None


def cmp(a, b, tol=TOL):
    """True se ambos são None, ou se diferem menos que tol."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) < tol


def norm(s):
    """Normaliza string para comparação (uppercase, strip)."""
    return str(s or '').upper().strip()


def extract_complementar_key(nome):
    """
    Extrai a chave cartório de um nome de espaço complementar do CV CRM.

    Regras:
    - Garagem comercial n° CN  →  GC{N:02d}  (ex.: "C01" → "GC01")
    - Garagem (qualquer tipo)  →  G{n:02d}   (ex.: 57 → "G57")
    - Moto standalone          →  M{n}       (ex.: "M11" → "M11")
    - Hobby Box standalone     →  HB{n:02d}  (ex.: 57 → "HB57")
    """
    if not nome:
        return None
    low = nome.lower()

    # Moto sem garagem: "Vaga de moto n° M11"
    if 'moto' in low and 'garagem' not in low and 'vaga' not in low.replace('vaga de moto', ''):
        m = re.search(r'(M\d+)', nome, re.IGNORECASE)
        if m:
            return m.group(1).upper()

    # Garagem comercial: "Vaga de garagem comercial n° C01"
    if 'comercial' in low:
        m = re.search(r'n[º°]?\s*(C\d+)', nome, re.IGNORECASE)
        if m:
            return f"GC{m.group(1)[1:].zfill(2)}"

    # Qualquer garagem (estendida, regular, etc.)
    if 'garagem' in low or 'vaga estendida' in low or 'vaga de garagem' in low:
        # "estendida n° 135" ou "estendida n°135" ou "estendida 129"
        m = re.search(r'estendida\s*n[º°]?\s*(\d+)', nome, re.IGNORECASE)
        if m:
            return f"G{int(m.group(1)):02d}"
        # "garagem n° 57"
        m = re.search(r'garagem\s*n[º°]?\s*(\d+)', nome, re.IGNORECASE)
        if m:
            return f"G{int(m.group(1)):02d}"
        # "Vaga estendida 25 e Hobby Box 28" (sem "n°")
        m = re.search(r'(?:vaga\s+)?estendida\s+(\d+)', nome, re.IGNORECASE)
        if m:
            return f"G{int(m.group(1)):02d}"

    # Moto standalone (após excluir garagem acima): "Vaga de moto n° M11"
    if 'moto' in low and 'garagem' not in low:
        m = re.search(r'(M\d+)', nome, re.IGNORECASE)
        if m:
            return m.group(1).upper()

    # Hobby Box standalone: "Hobby Box n° 57"
    if 'hobby' in low or 'hbox' in low or 'h box' in low:
        m = re.search(r'(?:hobby\s*box|hbox|h\s*box)\s*n[º°]?\s*(\d+)', nome, re.IGNORECASE)
        if m:
            return f"HB{int(m.group(1)):02d}"

    return None


# ---------------------------------------------------------------------------
# Carregamento do cartório
# ---------------------------------------------------------------------------

def load_cartorio(xlsx_path):
    """
    Retorna:
        unidades    dict  norm(unidade) → row   (apartamentos + lojas)
        complementares  dict  chave → row  (garagens + HBs + motos)
    """
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb['cartorio']
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    data = [dict(zip(header, r)) for r in rows[1:] if r[0] is not None]
    data = [r for r in data if r.get('tipo')]

    unidades = {}
    complementares = {}

    for row in data:
        tipo = (row.get('tipo') or '').lower()
        unidade = row.get('unidade')
        if unidade is None:
            continue
        key = norm(str(unidade))
        if tipo in ('apartamento', 'loja'):
            unidades[key] = row
        elif tipo in ('garagem', 'hobby box', 'moto'):
            complementares[key] = row

    return unidades, complementares


# ---------------------------------------------------------------------------
# Conexão CDP (idêntico ao importar_cvcrm)
# ---------------------------------------------------------------------------

def debug_port_alive(port):
    import urllib.request
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version', timeout=1)
        return True
    except Exception:
        return False


def connect_or_launch(p, chrome_path, profile_dir, port, target_url, stdout):
    if debug_port_alive(port):
        return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')

    subprocess.Popen([
        chrome_path,
        f'--remote-debugging-port={port}',
        f'--user-data-dir={profile_dir}',
        target_url,
    ])
    for _ in range(15):
        time.sleep(1)
        if debug_port_alive(port):
            break
    else:
        raise CommandError('O Chrome não abriu a debugging port a tempo.')

    stdout.write(
        'Faça login manualmente na janela do Chrome que abriu '
        '(e-mail, senha e o desafio de segurança do Cloudflare).'
    )
    input('Pressione ENTER depois de estar logado e na tela do empreendimento... ')
    return p.chromium.connect_over_cdp(f'http://127.0.0.1:{port}')


# ---------------------------------------------------------------------------
# Coleta de dados do CV CRM
# ---------------------------------------------------------------------------

def get_unidades_cvcrm(page, base, emp_id):
    """Baixa CSV export de unidades; retorna lista de dicts."""
    url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/exportar_unidades_download'
    resp = page.request.get(url)
    if resp.status != 200:
        raise CommandError(f'Falha ao baixar export de unidades (status {resp.status}).')
    text = resp.body().decode('utf-8-sig')

    lines = text.splitlines()
    try:
        header_idx = next(i for i, l in enumerate(lines) if 'ID Unidade' in l)
    except StopIteration:
        raise CommandError('CSV de Unidades não encontrado — verifique se está logado.')

    nfields = lines[header_idx].count(';') + 1
    data_lines = []
    for line in lines[header_idx + 1:]:
        if line.count(';') + 1 < nfields:
            break
        data_lines.append(line)

    reader = csv.DictReader([lines[header_idx]] + data_lines, delimiter=';')
    return list(reader)


def get_tipologia_tipo_maps(page, base, emp_id, sample_unit_id):
    """Carrega um formulário de edição de unidade para obter os mapeamentos de tipologia/tipo."""
    url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/unidades/{sample_unit_id}/editar'
    resp = page.request.get(url)
    tree = lxml.html.fromstring(resp.text())

    def select_map(field_id):
        result = {}
        el = tree.get_element_by_id(field_id, None)
        if el is None:
            return result
        for opt in el.xpath('.//option'):
            val = opt.get('value')
            if val:
                result[val] = (opt.text or '').strip()
        return result

    return select_map('idtipologia'), select_map('idtipo')


def get_complementares_cvcrm(page, base, emp_id, stdout):
    """Coleta todos os espaços complementares via formulários de edição."""
    list_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/espacoscomplementares'
    resp = page.request.get(list_url)
    ids = sorted(set(int(m) for m in re.findall(r'espacoscomplementares/(\d+)/opcoes', resp.text())))

    rows = []
    for i, esp_id in enumerate(ids, 1):
        url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/espacoscomplementares/{esp_id}/editar'
        r = page.request.get(url)
        if r.status != 200:
            stdout.write(f'  Falhou espaço {esp_id} (status {r.status}), pulando.')
            continue
        tree = lxml.html.fromstring(r.text())

        def val(fid):
            el = tree.get_element_by_id(fid, None)
            return el.get('value', '') if el is not None else ''

        def textarea(fid):
            el = tree.get_element_by_id(fid, None)
            return (el.text_content() or '').strip() if el is not None else ''

        rows.append({
            'nome': val('nome'),
            'andar_descricao': textarea('andar_descricao'),
            'area': to_float_br(val('area')),
            'area_comum': to_float_br(val('area_comum')),
            'valor': to_float_br(val('valor')),
            'fracao_ideal': to_float_br(val('fracao_ideal')),
        })
        if i % 25 == 0 or i == len(ids):
            stdout.write(f'  {i}/{len(ids)} complementares processados...')

    return rows


# ---------------------------------------------------------------------------
# Comparações
# ---------------------------------------------------------------------------

def compare_unidades(cvcrm_rows, tipologia_map, tipo_map, cartorio_unidades):
    """
    Retorna (divergencias, sem_match_cvcrm, sem_match_cartorio).
    divergencias: list of (nome, campo, valor_cartorio, valor_cvcrm)
    """
    divergencias = []
    sem_match_cvcrm = []
    cartorio_usados = set()

    for row in cvcrm_rows:
        nome_cv = row.get('Unidade', '').strip()
        key = norm(nome_cv)
        cart = cartorio_unidades.get(key)

        if cart is None:
            sem_match_cvcrm.append(nome_cv)
            continue

        cartorio_usados.add(key)

        tipologia_cv = tipologia_map.get(row.get('ID Tipologia', ''), '').strip()
        tipologia_ct = str(cart.get('tipologia') or '').strip()

        # Comparar tipologia (só para não-lojas)
        if cart.get('tipo', '').lower() == 'apartamento':
            if norm(tipologia_cv) != norm(tipologia_ct):
                divergencias.append((nome_cv, 'Tipologia', tipologia_ct or '(vazio)', tipologia_cv or '(vazio)'))

        area_priv_cv = to_float_csv(row.get('Área privativa', ''))
        area_priv_ct = cart.get('área privativa')
        if not cmp(area_priv_ct, area_priv_cv):
            divergencias.append((nome_cv, 'Área privativa m²', area_priv_ct, area_priv_cv))

        area_com_cv = to_float_csv(row.get('Área comum', ''))
        area_com_ct = cart.get('área de uso comum')
        if not cmp(area_com_ct, area_com_cv):
            divergencias.append((nome_cv, 'Área comum m²', area_com_ct, area_com_cv))

        area_tot_cv = to_float_csv(row.get('Área total', ''))
        area_tot_ct = cart.get('área real total')
        if not cmp(area_tot_ct, area_tot_cv):
            divergencias.append((nome_cv, 'Área total m²', area_tot_ct, area_tot_cv))

        fracao_cv = to_float_csv(row.get('Fração Ideal', ''))
        fracao_ct = cart.get('fração ideal')
        if not cmp(fracao_ct, fracao_cv):
            divergencias.append((nome_cv, 'Fração ideal %', fracao_ct, fracao_cv))

    sem_match_cartorio = [k for k in cartorio_unidades if k not in cartorio_usados]
    return divergencias, sem_match_cvcrm, sem_match_cartorio


def compare_complementares(cvcrm_rows, cartorio_complementares):
    """
    Retorna (divergencias, sem_match_cvcrm, sem_match_cartorio).
    """
    divergencias = []
    sem_match_cvcrm = []
    cartorio_usados = set()

    for row in cvcrm_rows:
        nome = row.get('nome', '')
        key = extract_complementar_key(nome)

        if key is None:
            sem_match_cvcrm.append(f'{nome!r}  [chave não extraída]')
            continue

        cart = cartorio_complementares.get(key)
        if cart is None:
            sem_match_cvcrm.append(f'{nome!r}  [chave={key} não encontrada no cartório]')
            continue

        cartorio_usados.add(key)

        # área privativa total (CV CRM 'area' = cartório 'área privativa total')
        area_priv_tot_ct = cart.get('área privativa total')
        area_cv = row.get('area')
        if not cmp(area_priv_tot_ct, area_cv):
            divergencias.append((nome, 'Área privativa total m²', area_priv_tot_ct, area_cv))

        # área comum
        area_com_ct = cart.get('área de uso comum')
        area_com_cv = row.get('area_comum')
        if not cmp(area_com_ct, area_com_cv):
            divergencias.append((nome, 'Área comum m²', area_com_ct, area_com_cv))

        # fração ideal
        fracao_ct = cart.get('fração ideal')
        fracao_cv = row.get('fracao_ideal')
        if not cmp(fracao_ct, fracao_cv):
            divergencias.append((nome, 'Fração ideal %', fracao_ct, fracao_cv))

    sem_match_cartorio = [k for k in cartorio_complementares if k not in cartorio_usados]
    return divergencias, sem_match_cvcrm, sem_match_cartorio


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Verifica dados do CV CRM contra o cartório (cartorio.xlsx) e lista divergências.'

    def add_arguments(self, parser):
        parser.add_argument('--empreendimento', type=int, default=3,
                            help='ID do empreendimento no CV CRM (padrão: 3)')
        parser.add_argument('--cartorio', type=str, default=None,
                            help='Caminho do cartorio.xlsx (padrão: cartorio.xlsx na raiz do projeto)')
        parser.add_argument('--chrome-path', type=str, default=None)
        parser.add_argument('--debug-port', type=int, default=9222)
        parser.add_argument('--profile-dir', type=str, default=None)
        parser.add_argument('--so-divergencias', action='store_true',
                            help='Omite linhas OK, mostra apenas divergências e sem-match')

    def handle(self, *args, **options):
        from playwright.sync_api import sync_playwright

        cartorio_path = options['cartorio'] or str(Path(settings.BASE_DIR) / 'cartorio.xlsx')
        if not Path(cartorio_path).exists():
            raise CommandError(f'Arquivo não encontrado: {cartorio_path}')

        emp_id = options['empreendimento']
        port = options['debug_port']
        chrome_path = options['chrome_path'] or find_chrome()
        profile_dir = options['profile_dir'] or str(Path(settings.BASE_DIR) / '.cvcrm_chrome_profile')
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        base = 'https://cota.cvcrm.com.br'
        target_url = f'{base}/gestor/cadastros/empreendimentos/{emp_id}/administrar#unidades'

        self.stdout.write(f'Carregando {cartorio_path}...')
        cartorio_unidades, cartorio_complementares = load_cartorio(cartorio_path)
        self.stdout.write(
            f'  Cartório: {len(cartorio_unidades)} unidades, '
            f'{len(cartorio_complementares)} espaços complementares.'
        )

        with sync_playwright() as p:
            browser = connect_or_launch(p, chrome_path, profile_dir, port, target_url, self.stdout)
            ctx = browser.contexts[0]
            page = next((pg for pg in ctx.pages if 'cvcrm.com.br' in pg.url), ctx.pages[0])

            try:
                page.wait_for_load_state('load', timeout=15000)
            except Exception:
                pass
            page.wait_for_timeout(2000)

            while page.locator('input[type="password"]').count() > 0:
                self.stdout.write(self.style.WARNING(
                    'Faça login manualmente na janela do Chrome e pressione ENTER aqui...'
                ))
                input()
                page.wait_for_timeout(2000)

            # --- Unidades ---
            self.stdout.write('\nBaixando Unidades (CSV)...')
            cv_unidades = get_unidades_cvcrm(page, base, emp_id)
            self.stdout.write(f'  {len(cv_unidades)} unidades no CV CRM.')

            if cv_unidades:
                sample_id = cv_unidades[0]['ID Unidade']
                tipologia_map, tipo_map = get_tipologia_tipo_maps(page, base, emp_id, sample_id)
            else:
                tipologia_map, tipo_map = {}, {}

            # --- Espaços Complementares ---
            self.stdout.write('\nColetando Espaços Complementares (pode demorar alguns minutos)...')
            cv_complementares = get_complementares_cvcrm(page, base, emp_id, self.stdout)
            self.stdout.write(f'  {len(cv_complementares)} complementares no CV CRM.')

        # --- Comparações ---
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write('RESULTADO DA VERIFICAÇÃO')
        self.stdout.write('=' * 70)

        div_u, sem_cv_u, sem_ct_u = compare_unidades(
            cv_unidades, tipologia_map, tipo_map, cartorio_unidades
        )
        div_c, sem_cv_c, sem_ct_c = compare_complementares(
            cv_complementares, cartorio_complementares
        )

        # Unidades
        self.stdout.write(f'\n--- UNIDADES ({len(cv_unidades)} no CV CRM × {len(cartorio_unidades)} no cartório) ---')
        if div_u:
            self.stdout.write(self.style.ERROR(f'\n{len(div_u)} DIVERGÊNCIA(S) EM UNIDADES:'))
            self.stdout.write(f'  {"Unidade":<12}  {"Campo":<22}  {"Cartório":>12}  {"CV CRM":>12}')
            self.stdout.write(f'  {"-"*12}  {"-"*22}  {"-"*12}  {"-"*12}')
            for nome, campo, ct, cv in div_u:
                self.stdout.write(f'  {nome:<12}  {campo:<22}  {str(ct):>12}  {str(cv):>12}')
        else:
            self.stdout.write(self.style.SUCCESS('  Nenhuma divergência em Unidades.'))

        if sem_cv_u:
            self.stdout.write(self.style.WARNING(
                f'\n  {len(sem_cv_u)} unidade(s) do CV CRM sem correspondência no cartório:'
            ))
            for n in sem_cv_u:
                self.stdout.write(f'    {n}')

        if sem_ct_u:
            self.stdout.write(self.style.WARNING(
                f'\n  {len(sem_ct_u)} unidade(s) do cartório sem correspondência no CV CRM:'
            ))
            for k in sem_ct_u:
                self.stdout.write(f'    {k}')

        # Complementares
        self.stdout.write(
            f'\n--- ESPAÇOS COMPLEMENTARES ({len(cv_complementares)} no CV CRM × '
            f'{len(cartorio_complementares)} no cartório) ---'
        )
        if div_c:
            self.stdout.write(self.style.ERROR(f'\n{len(div_c)} DIVERGÊNCIA(S) EM COMPLEMENTARES:'))
            self.stdout.write(f'  {"Nome CV CRM":<50}  {"Campo":<25}  {"Cartório":>10}  {"CV CRM":>10}')
            self.stdout.write(f'  {"-"*50}  {"-"*25}  {"-"*10}  {"-"*10}')
            for nome, campo, ct, cv in div_c:
                self.stdout.write(f'  {nome:<50}  {campo:<25}  {str(ct):>10}  {str(cv):>10}')
        else:
            self.stdout.write(self.style.SUCCESS('  Nenhuma divergência em Espaços Complementares.'))

        if sem_cv_c:
            self.stdout.write(self.style.WARNING(
                f'\n  {len(sem_cv_c)} complementar(es) do CV CRM sem correspondência no cartório:'
            ))
            for n in sem_cv_c:
                self.stdout.write(f'    {n}')

        if sem_ct_c:
            self.stdout.write(self.style.WARNING(
                f'\n  {len(sem_ct_c)} complementar(es) do cartório sem correspondência no CV CRM:'
            ))
            for k in sem_ct_c:
                self.stdout.write(f'    {k}')

        # Resumo
        total_div = len(div_u) + len(div_c)
        total_sem = len(sem_cv_u) + len(sem_ct_u) + len(sem_cv_c) + len(sem_ct_c)
        self.stdout.write('\n' + '=' * 70)
        if total_div == 0 and total_sem == 0:
            self.stdout.write(self.style.SUCCESS('TUDO OK — nenhuma divergência encontrada.'))
        else:
            self.stdout.write(
                self.style.ERROR(
                    f'TOTAL: {total_div} divergência(s), {total_sem} entrada(s) sem correspondência.'
                )
            )
        self.stdout.write('=' * 70)
