import csv
import io
import json
import re
from datetime import datetime, date
from collections import defaultdict, OrderedDict

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db import transaction

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

from .models import (
    ImportLog, Tabela, Permuta, Vinculo, Venda,
    Unidade, FluxoContrato, FluxoParcela, Comissao,
)

# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------

def _parse_float(s):
    if not s or s.strip() in ('', '-', '—'):
        return 0.0
    cleaned = s.strip().replace('.', '').replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_date(s):
    if not s:
        return None
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            continue
    return None


def _fmt_brl(value):
    if value == 0:
        return 'R$ 0,00'
    formatted = f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {formatted}'


def _fmt_m2(value):
    if value == 0:
        return '0,00 m²'
    formatted = f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'{formatted} m²'


def _add_months(dt, n):
    month = dt.month - 1 + n
    year = dt.year + month // 12
    month = month % 12 + 1
    return datetime(year, month, 1)


def _parse_tabela_m2(s):
    return _parse_float(s.replace('m²', '').replace('m2', ''))


def _parse_tabela_brl(s):
    return _parse_float(s.replace('R$', ''))


def _open_csv(file_obj):
    raw = file_obj.read()
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    return io.StringIO(raw.decode('utf-8'))


# ---------------------------------------------------------------------------
# Leitura de dados — ORM
# ---------------------------------------------------------------------------

def _load_tabela():
    return {t.unidade: t.valor_total for t in Tabela.objects.all()}


def _load_permutas():
    return set(Permuta.objects.values_list('unidade', flat=True))


def _load_vinculos():
    return {
        v.unidade: {'garagens': v.garagens, 'hb': v.hb}
        for v in Vinculo.objects.all()
    }


def _load_vendas():
    return [
        {
            'numero':       v.numero,
            'situacao':     v.situacao,
            'unidade':      v.unidade,
            'm2':           v.m2,
            'cliente':      v.cliente,
            'imobiliaria':  v.imobiliaria,
            'espacos':      v.espacos,
        }
        for v in Venda.objects.all()
    ]


def _load_fluxo():
    rows = []
    for c in FluxoContrato.objects.prefetch_related('parcelas').all():
        monthly = [0.0] * 45
        for p in c.parcelas.all():
            if 0 <= p.mes_idx < 45:
                monthly[p.mes_idx] = p.valor
        rows.append({
            'id':              c.id_contrato,
            'cliente':         c.cliente,
            'unidade':         c.unidade,
            'empreendimento':  c.empreendimento,
            'vgv':             c.vgv,
            'pv':              c.pv,
            'primeira_parcela': datetime(c.primeira_parcela.year,
                                         c.primeira_parcela.month,
                                         c.primeira_parcela.day),
            'ultima_parcela':  datetime(c.ultima_parcela.year,
                                        c.ultima_parcela.month,
                                        c.ultima_parcela.day)
                               if c.ultima_parcela else None,
            'monthly':         monthly,
            'imobiliaria':     c.imobiliaria,
            'corretor':        c.corretor,
        })
    return rows


def _build_monthly_totals(fluxo_rows):
    totals = defaultdict(float)
    for c in fluxo_rows:
        base = c['primeira_parcela'].replace(day=1)
        for i, amt in enumerate(c['monthly']):
            if amt:
                key = _add_months(base, i).strftime('%m/%Y')
                totals[key] += amt
    return OrderedDict(
        sorted(totals.items(), key=lambda x: datetime.strptime(x[0], '%m/%Y'))
    )


# ---------------------------------------------------------------------------
# Resumos — ORM
# ---------------------------------------------------------------------------

def _compute_resumos_tabela():
    sit_vt = defaultdict(float)
    sit_ap = defaultdict(float)
    sit_n  = defaultdict(int)
    tip_vt     = defaultdict(float)
    tip_ap     = defaultdict(float)
    tip_n      = defaultdict(int)
    tip_est_vt = defaultdict(float)
    tip_est_ap = defaultdict(float)
    tip_est_n  = defaultdict(int)

    permutas = _load_permutas()

    for t in Tabela.objects.all():
        sit = 'Permuta' if t.unidade in permutas else t.situacao
        tip = t.tipologia
        sit_vt[sit] += t.valor_total
        sit_ap[sit] += t.area_privativa
        sit_n[sit]  += 1
        if tip:
            tip_vt[tip] += t.valor_total
            tip_ap[tip] += t.area_privativa
            tip_n[tip]  += 1
            if sit in ('Disponível', 'Reservada'):
                tip_est_vt[tip] += t.valor_total
                tip_est_ap[tip] += t.area_privativa
                tip_est_n[tip]  += 1

    total_vt = sum(sit_vt.values()) or 1
    total_ap = sum(sit_ap.values()) or 1
    total_n  = sum(sit_n.values())  or 1

    SIT_ORDER = ['Disponível', 'Reservada', 'Bloqueada', 'Vendida', 'Permuta', 'QA']
    all_sits = sorted(sit_n.keys(), key=lambda s: SIT_ORDER.index(s) if s in SIT_ORDER else 99)

    resumo_sit = []
    for s in all_sits:
        resumo_sit.append({
            'situacao': s,
            'vt_fmt':   _fmt_brl(sit_vt[s]),
            'pct_vt':   f"{sit_vt[s]/total_vt*100:.2f}%",
            'ap_fmt':   _fmt_m2(sit_ap[s]),
            'pct_ap':   f"{sit_ap[s]/total_ap*100:.2f}%",
            'n':        sit_n[s],
            'pct_n':    f"{sit_n[s]/total_n*100:.2f}%",
        })
    resumo_sit.append({
        'situacao': 'Total Geral',
        'vt_fmt':   _fmt_brl(sum(sit_vt.values())),
        'pct_vt':   '100,00%',
        'ap_fmt':   _fmt_m2(sum(sit_ap.values())),
        'pct_ap':   '100,00%',
        'n':        total_n,
        'pct_n':    '100,00%',
        'is_total': True,
    })

    LIQUIDO_SITS = ['Disponível', 'Reservada', 'Vendida']
    liq_vt = sum(sit_vt.get(s, 0.0) for s in LIQUIDO_SITS)
    liq_ap = sum(sit_ap.get(s, 0.0) for s in LIQUIDO_SITS)
    liq_n  = sum(sit_n.get(s, 0)    for s in LIQUIDO_SITS)
    resumo_sit_liquido = []
    for s in LIQUIDO_SITS:
        if s not in sit_n:
            continue
        resumo_sit_liquido.append({
            'situacao': s,
            'vt_fmt':   _fmt_brl(sit_vt[s]),
            'pct_vt':   f"{sit_vt[s]/liq_vt*100:.2f}%" if liq_vt else '0,00%',
            'ap_fmt':   _fmt_m2(sit_ap[s]),
            'pct_ap':   f"{sit_ap[s]/liq_ap*100:.2f}%" if liq_ap else '0,00%',
            'n':        sit_n[s],
            'pct_n':    f"{sit_n[s]/liq_n*100:.2f}%" if liq_n else '0,00%',
        })
    resumo_sit_liquido.append({
        'situacao': 'Total Geral Líquido',
        'vt_fmt':   _fmt_brl(liq_vt),
        'pct_vt':   '100,00%',
        'ap_fmt':   _fmt_m2(liq_ap),
        'pct_ap':   '100,00%',
        'n':        liq_n,
        'pct_n':    '100,00%',
        'is_total': True,
    })

    def _grupo(t):
        tl = t.lower()
        if 'studio' in tl: return 'Studio'
        if 'loja'   in tl: return 'Loja'
        return '2D'

    grp_vt = defaultdict(float)
    grp_ap = defaultdict(float)
    grp_n  = defaultdict(int)
    for t in tip_n:
        g = _grupo(t)
        grp_vt[g] += tip_vt[t]
        grp_ap[g] += tip_ap[t]
        grp_n[g]  += tip_n[t]

    total_tip_vt = sum(grp_vt.values()) or 1
    total_tip_ap = sum(grp_ap.values()) or 1
    total_tip_n  = sum(grp_n.values())
    preco_medio  = total_tip_vt / total_tip_n if total_tip_n else 0

    GRP_ORDER = ['Studio', '2D', 'Loja']
    all_grps = sorted(grp_n.keys(), key=lambda g: GRP_ORDER.index(g) if g in GRP_ORDER else 99)

    resumo_tip = []
    for g in all_grps:
        rsm2 = grp_vt[g] / grp_ap[g] if grp_ap[g] else 0
        resumo_tip.append({
            'n':      grp_n[g],
            'tipo':   g,
            'ap_fmt': f"{grp_ap[g]:,.2f}".replace(',','X').replace('.',',').replace('X','.'),
            'vt_fmt': _fmt_brl(grp_vt[g]),
            'rsm2':   f"{rsm2:,.2f}".replace(',','X').replace('.',',').replace('X','.'),
        })
    resumo_tip.append({
        'n':      total_tip_n,
        'tipo':   'Total',
        'ap_fmt': f"{total_tip_ap:,.2f}".replace(',','X').replace('.',',').replace('X','.'),
        'vt_fmt': _fmt_brl(total_tip_vt),
        'rsm2':   f"{total_tip_vt/total_tip_ap:,.2f}".replace(',','X').replace('.',',').replace('X','.')
                  if total_tip_ap else '0,00',
        'is_total': True,
    })

    est_grp_vt = defaultdict(float)
    est_grp_ap = defaultdict(float)
    est_grp_n  = defaultdict(int)
    for t in tip_est_n:
        g = _grupo(t)
        est_grp_vt[g] += tip_est_vt[t]
        est_grp_ap[g] += tip_est_ap[t]
        est_grp_n[g]  += tip_est_n[t]

    total_est_vt = sum(est_grp_vt.values()) or 1
    total_est_ap = sum(est_grp_ap.values()) or 1
    total_est_n  = sum(est_grp_n.values())
    preco_medio_estoque = total_est_vt / total_est_n if total_est_n else 0

    all_est_grps = sorted(est_grp_n.keys(), key=lambda g: GRP_ORDER.index(g) if g in GRP_ORDER else 99)

    resumo_tip_estoque = []
    for g in all_est_grps:
        rsm2 = est_grp_vt[g] / est_grp_ap[g] if est_grp_ap[g] else 0
        resumo_tip_estoque.append({
            'n':      est_grp_n[g],
            'tipo':   g,
            'ap_fmt': f"{est_grp_ap[g]:,.2f}".replace(',','X').replace('.',',').replace('X','.'),
            'vt_fmt': _fmt_brl(est_grp_vt[g]),
            'rsm2':   f"{rsm2:,.2f}".replace(',','X').replace('.',',').replace('X','.'),
        })
    resumo_tip_estoque.append({
        'n':      total_est_n,
        'tipo':   'Total',
        'ap_fmt': f"{total_est_ap:,.2f}".replace(',','X').replace('.',',').replace('X','.'),
        'vt_fmt': _fmt_brl(total_est_vt),
        'rsm2':   f"{total_est_vt/total_est_ap:,.2f}".replace(',','X').replace('.',',').replace('X','.')
                  if total_est_ap else '0,00',
        'is_total': True,
    })

    return (
        resumo_sit,
        resumo_sit_liquido,
        resumo_tip,
        resumo_tip_estoque,
        _fmt_brl(preco_medio),
        _fmt_brl(preco_medio_estoque),
        sum(sit_vt.values()),
        sit_vt.get('Permuta',    0.0),
        sit_vt.get('Disponível', 0.0),
        sit_vt.get('Reservada',  0.0),
    )


# ---------------------------------------------------------------------------
# Unidades — ORM
# ---------------------------------------------------------------------------

UNIDADE_HEADERS = [
    'Unidade', 'Tipo', 'Complemento do Tipo',
    'Area Privativa', 'Area Priv. Acessoria', 'Area Comum', 'Fracao Ideal',
    'Garagens', 'HB', 'Preço Tabela', 'Status', 'Preço de Venda',
]


def _load_unidades():
    sold_units  = set(Venda.objects.values_list('unidade', flat=True))
    vgv_by_unit = {c.unidade: c.vgv for c in FluxoContrato.objects.all()}
    vinculos    = _load_vinculos()
    tabela      = _load_tabela()
    permutas    = _load_permutas()

    data = []
    for u in Unidade.objects.all():
        un = u.unidade
        vinc = vinculos.get(un, {})
        if un in permutas:
            status = 'Permuta'
        elif un in sold_units:
            status = 'Vendido'
        else:
            status = 'Disponível'
        data.append([
            un,
            u.tipo,
            u.complemento_tipo,
            u.area_privativa,
            u.area_priv_acessoria,
            u.area_comum,
            u.fracao_ideal,
            vinc.get('garagens', ''),
            vinc.get('hb', ''),
            tabela.get(un, ''),
            status,
            vgv_by_unit.get(un, ''),
        ])
    return UNIDADE_HEADERS, data


def _compute_areas():
    qs = Unidade.objects.all()
    area_priv       = sum(u.area_privativa      for u in qs)
    area_priv_acess = sum(u.area_priv_acessoria for u in qs)
    area_comum      = sum(u.area_comum          for u in qs)
    total_priv      = area_priv + area_priv_acess
    area_total      = total_priv + area_comum
    return area_priv, area_priv_acess, total_priv, area_comum, area_total


# ---------------------------------------------------------------------------
# Importação de CSVs
# ---------------------------------------------------------------------------

def _col(*names):
    def getter(row):
        for n in names:
            v = row.get(n)
            if v is not None:
                return v
        row_lower = {k.lower(): v for k, v in row.items()}
        for n in names:
            v = row_lower.get(n.lower())
            if v is not None:
                return v
        return ''
    return getter


@transaction.atomic
def _import_tabela(file_obj, nome):
    f = _open_csv(file_obj)
    objs = []
    get_unidade  = _col('UNIDADE')
    get_tipo     = _col('TIPOLOGIA')
    get_sit      = _col('SITUAÇÃO', 'SITUACAO', 'Situação', 'Situacao')
    get_area     = _col('ÁREA PRIVATIVA', 'AREA PRIVATIVA', 'Área Privativa', 'Area Privativa')
    get_valor    = _col('VALOR TOTAL', 'Valor Total')
    for r in csv.DictReader(f, delimiter=';'):
        u = get_unidade(r).strip()
        if not u:
            continue
        objs.append(Tabela(
            unidade        = u,
            tipologia      = get_tipo(r).strip(),
            situacao       = get_sit(r).strip(),
            area_privativa = _parse_tabela_m2(get_area(r)),
            valor_total    = _parse_tabela_brl(get_valor(r)),
        ))
    if not objs:
        raise ValueError('Nenhuma linha válida encontrada. Verifique o delimitador (;) e o cabeçalho.')
    Tabela.objects.all().delete()
    Tabela.objects.bulk_create(objs)
    ImportLog.objects.create(tipo='tabela', total_registros=len(objs), nome_arquivo=nome)
    vgv = sum(o.valor_total for o in objs)
    return len(objs), {'VGV total': _fmt_brl(vgv)}


@transaction.atomic
def _import_permutas(file_obj, nome):
    f = _open_csv(file_obj)
    unidades = []
    for row in csv.reader(f):
        u = row[0].strip() if row else ''
        if u:
            unidades.append(u)
    if not unidades:
        raise ValueError('Arquivo vazio ou sem unidades válidas.')
    Permuta.objects.all().delete()
    Permuta.objects.bulk_create([Permuta(unidade=u) for u in unidades])
    ImportLog.objects.create(tipo='permutas', total_registros=len(unidades), nome_arquivo=nome)
    return len(unidades), {}


@transaction.atomic
def _import_vinculos(file_obj, nome):
    f = _open_csv(file_obj)
    objs = []
    for r in csv.DictReader(f, delimiter=';'):
        u = r.get('Unidade', '').strip()
        if u:
            objs.append(Vinculo(
                unidade  = u,
                garagens = r.get('Garagens', '').strip(),
                hb       = r.get('HB', '').strip(),
            ))
    if not objs:
        raise ValueError('Nenhuma linha válida encontrada.')
    Vinculo.objects.all().delete()
    Vinculo.objects.bulk_create(objs)
    ImportLog.objects.create(tipo='vinculo', total_registros=len(objs), nome_arquivo=nome)
    return len(objs), {}


@transaction.atomic
def _import_vendas(file_obj, nome):
    f = _open_csv(file_obj)
    objs = []
    get_sit     = _col('Situação', 'Situacao', 'SITUAÇÃO')
    get_m2      = _col('M² da unidade', 'M2 da unidade', 'M da unidade')
    get_imob    = _col('Imobiliária', 'Imobiliaria', 'IMOBILIÁRIA')
    get_espacos = _col('Espaços complementares', 'Espacos complementares')
    for row in csv.DictReader(f, delimiter=';'):
        reserva_raw = row.get('Reserva', '')
        if not reserva_raw.strip():
            continue
        if 'HIPERLINK' in reserva_raw:
            m = re.search(r'"(\d+)"\)', reserva_raw)
            reserva = m.group(1) if m else ''
        else:
            reserva = reserva_raw.strip()
        if not reserva.isdigit():
            continue
        cliente_raw = row.get('Cliente', '')
        if 'HIPERLINK' in cliente_raw:
            m = re.search(r';"([^"]+)"\)', cliente_raw)
            cliente = m.group(1) if m else cliente_raw.strip()
        else:
            cliente = cliente_raw.strip()
        objs.append(Venda(
            numero      = reserva,
            situacao    = get_sit(row).strip(),
            unidade     = row.get('Unidade', '').strip(),
            m2          = get_m2(row).strip(),
            cliente     = cliente,
            imobiliaria = get_imob(row).strip(),
            espacos     = get_espacos(row).strip(),
        ))
    if not objs:
        raise ValueError('Nenhuma reserva válida encontrada.')
    Venda.objects.all().delete()
    Venda.objects.bulk_create(objs)
    ImportLog.objects.create(tipo='vendas', total_registros=len(objs), nome_arquivo=nome)
    return len(objs), {}


@transaction.atomic
def _import_fluxo(file_obj, nome):
    f = _open_csv(file_obj)
    get_empr  = _col('Empreendimento', 'EMPREENDIMENTO')
    get_imob  = _col('Imobiliária', 'Imobiliaria', 'Imob. Coordenação', 'IMOBILIÁRIA')
    get_corr  = _col('Corretor', 'CORRETOR')
    get_ult   = _col('Última parcela', 'Ultima parcela', 'ÚLTIMA PARCELA')
    contratos = []
    for row in csv.DictReader(f, delimiter=';'):
        primeira = _parse_date(row.get('Primeira parcela', ''))
        if not primeira:
            continue
        ultima_dt = _parse_date(get_ult(row))
        c = FluxoContrato(
            id_contrato      = row.get('Id.', '').strip(),
            cliente          = row.get('Cliente', '').strip(),
            unidade          = row.get('Unidade', '').strip(),
            empreendimento   = get_empr(row).strip(),
            vgv              = _parse_float(row.get('VGV', '0')),
            pv               = _parse_float(row.get('PV', '0')),
            primeira_parcela = date(primeira.year, primeira.month, primeira.day),
            ultima_parcela   = date(ultima_dt.year, ultima_dt.month, ultima_dt.day)
                               if ultima_dt else None,
            imobiliaria      = get_imob(row).strip(),
            corretor         = get_corr(row).strip(),
        )
        monthly_raw = [_parse_float(row.get(f'Mês {i}', '0')) for i in range(45)]
        contratos.append((c, monthly_raw))
    if not contratos:
        raise ValueError('Nenhum contrato com data de primeira parcela encontrado.')
    FluxoContrato.objects.all().delete()
    saved = FluxoContrato.objects.bulk_create([c for c, _ in contratos])
    parcelas_bulk = []
    for contrato_obj, monthly in zip(saved, [m for _, m in contratos]):
        for i, val in enumerate(monthly):
            if val:
                parcelas_bulk.append(FluxoParcela(contrato=contrato_obj, mes_idx=i, valor=val))
    FluxoParcela.objects.bulk_create(parcelas_bulk)
    ImportLog.objects.create(tipo='fluxo', total_registros=len(saved), nome_arquivo=nome)
    vgv = sum(c.vgv for c, _ in contratos)
    return len(saved), {'VGV total': _fmt_brl(vgv), 'Parcelas': len(parcelas_bulk)}


@transaction.atomic
def _import_unidades(file_obj, nome):
    f = _open_csv(file_obj)
    get_ap  = _col('Area Privativa', 'Área Privativa', 'ÁREA PRIVATIVA', 'AREA PRIVATIVA')
    get_apa = _col('Area Priv. Acessoria', 'Área Priv. Acessoria', 'Area Priv Acessoria')
    get_ac  = _col('Area Comum', 'Área Comum', 'ÁREA COMUM')
    get_fi  = _col('Fracao Ideal', 'Fração Ideal', 'FRAÇÃO IDEAL')
    objs = []
    for r in csv.DictReader(f, delimiter=';'):
        u = r.get('Unidade', '').strip()
        if not u:
            continue
        objs.append(Unidade(
            unidade             = u,
            tipo                = r.get('Tipo', '').strip(),
            complemento_tipo    = r.get('Complemento do Tipo', '').strip(),
            area_privativa      = _parse_float(get_ap(r)),
            area_priv_acessoria = _parse_float(get_apa(r)),
            area_comum          = _parse_float(get_ac(r)),
            fracao_ideal        = get_fi(r).strip(),
        ))
    if not objs:
        raise ValueError('Nenhuma unidade válida encontrada.')
    Unidade.objects.all().delete()
    Unidade.objects.bulk_create(objs)
    ImportLog.objects.create(tipo='unidades', total_registros=len(objs), nome_arquivo=nome)
    area = sum(o.area_privativa for o in objs)
    return len(objs), {'Área privativa total': _fmt_m2(area)}


def _import_comissoes(f, nome):
    def _brl(s):
        s = str(s).strip().strip('"').replace('.', '').replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return 0.0

    def _col(row, *keys):
        for k in keys:
            v = row.get(k, '')
            if v.strip():
                return v.strip().strip('"')
        return ''

    for enc in ('utf-8-sig', 'latin-1'):
        try:
            raw = f.read().decode(enc)
            f.seek(0)
            break
        except Exception:
            f.seek(0)

    reader = csv.DictReader(raw.splitlines(), delimiter=';')

    csv_keys = set()
    count = 0
    with transaction.atomic():
        for row in reader:
            num = _col(row, 'Número', 'NÃºmero', 'Numero')
            if not num or not num.isdigit():
                continue

            beneficiario  = _col(row, 'Beneficiário', 'BeneficiÃ¡rio')
            tipo_comissao = _col(row, 'Tipo da comissão', 'Tipo da comissÃ£o')
            csv_keys.add((num, beneficiario, tipo_comissao))

            dados = {
                'reserva':              _col(row, 'Reserva'),
                'corretor':             _col(row, 'Corretor'),
                'imobiliaria':          _col(row, 'Imobiliária', 'ImobiliÃ¡ria'),
                'unidade':              _col(row, 'Unidade'),
                'cliente':              _col(row, 'Cliente'),
                'valor_contrato':       _brl(_col(row, 'Valor do contrato')),
                'valor_comissao_pagar': _brl(_col(row, 'Valor Comissão a pagar', 'Valor ComissÃ£o a pagar')),
                'valor_comissao':       _brl(_col(row, 'Valor da Comissão do Beneficiário',
                                                   'Valor da ComissÃ£o do BeneficiÃ¡rio')),
                'pct_comissao':         _brl(_col(row, 'Porcentagem da Comissão do Beneficiário',
                                                  'Porcentagem da ComissÃ£o do BeneficiÃ¡rio')),
            }

            try:
                obj = Comissao.objects.get(
                    numero=num, beneficiario=beneficiario, tipo_comissao=tipo_comissao)
                if obj.data_prevista or obj.data_pagamento:
                    continue  # protegido — tem data, não atualiza
                for k, v in dados.items():
                    setattr(obj, k, v)
                obj.save()
            except Comissao.DoesNotExist:
                Comissao.objects.create(
                    numero=num,
                    beneficiario=beneficiario,
                    tipo_comissao=tipo_comissao,
                    **dados,
                )
                count += 1

        # Remove apenas registros SEM datas que não estão no CSV
        pks_deletar = [
            obj.pk
            for obj in Comissao.objects.filter(
                data_prevista__isnull=True, data_pagamento__isnull=True)
            if (obj.numero, obj.beneficiario, obj.tipo_comissao) not in csv_keys
        ]
        if pks_deletar:
            Comissao.objects.filter(pk__in=pks_deletar).delete()

    total = sum(c.valor_comissao for c in Comissao.objects.all())
    return count, {'Valor total comissões': _fmt_brl(total)}


_IMPORTERS = {
    'tabela':     _import_tabela,
    'permutas':   _import_permutas,
    'vinculo':    _import_vinculos,
    'vendas':     _import_vendas,
    'fluxo':      _import_fluxo,
    'unidades':   _import_unidades,
    'comissoes':  _import_comissoes,
}

_LABELS = {
    'tabela':     'Tabela de Preços',
    'permutas':   'Permutas',
    'vinculo':    'Vínculos',
    'vendas':     'Vendas',
    'fluxo':      'Fluxo de Caixa',
    'unidades':   'Unidades',
    'comissoes':  'Comissões',
}


def comissoes_cadastro(request):
    def _parse_date(s):
        s = (s or '').strip()
        if not s:
            return None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        return None

    if request.method == 'POST':
        reserva = request.POST.get('reserva', '').strip()
        n = Comissao.objects.filter(reserva=reserva).update(
            data_prevista  = _parse_date(request.POST.get('data_prevista')),
            data_pagamento = _parse_date(request.POST.get('data_pagamento')),
        )
        if n:
            messages.success(request, f'Datas da reserva {reserva} atualizadas.')
        else:
            messages.error(request, f'Reserva {reserva} não encontrada.')
        return redirect('cota365:comissoes_cadastro')

    # Agrupa por reserva
    groups = defaultdict(list)
    for c in Comissao.objects.order_by('unidade', 'reserva', 'beneficiario'):
        groups[c.reserva].append(c)

    lista = []
    for reserva, records in groups.items():
        first  = records[0]
        extra  = len(records) - 1
        tem_premio = any(
            'premio' in r.tipo_comissao.lower() or 'prêmio' in r.tipo_comissao.lower()
            for r in records
        )
        outros_str = f'+{extra}{"P" if tem_premio else ""}' if extra > 0 else ''
        is_cota = 'COTA EMPREENDIMENTOS' in first.imobiliaria.upper()

        total_comissao = sum(r.valor_comissao for r in records)
        data_prevista  = next((r.data_prevista  for r in records if r.data_prevista),  None)
        data_pagamento = next((r.data_pagamento for r in records if r.data_pagamento), None)

        parceiros = [
            {'beneficiario': r.beneficiario,
             'tipo':         r.tipo_comissao,
             'valor':        _fmt_brl(r.valor_comissao)}
            for r in records
        ]

        lista.append({
            'reserva':            reserva,
            'unidade':            first.unidade,
            'cliente':            first.cliente,
            'imobiliaria':        first.imobiliaria,
            'total_fmt':          _fmt_brl(total_comissao),
            'outros_str':         outros_str,
            'tem_premio':         tem_premio,
            'is_cota':            is_cota,
            'data_prevista_iso':  data_prevista.strftime('%Y-%m-%d')  if data_prevista  else '',
            'data_pagamento_iso': data_pagamento.strftime('%Y-%m-%d') if data_pagamento else '',
            'pago':               bool(data_pagamento),
            'tem_data':           bool(data_prevista or data_pagamento),
            'parceiros_json':     json.dumps(parceiros, ensure_ascii=False),
            'total_json':         _fmt_brl(total_comissao),
        })

    lista.sort(key=lambda x: x['unidade'])
    return render(request, 'cota365/comissoes_cadastro.html', {
        'lista':   lista,
        'total_n': len(lista),
    })


def delete_reserva(request, reserva):
    if request.method == 'POST':
        n, _ = Comissao.objects.filter(reserva=reserva).delete()
        if n:
            messages.success(request, f'Reserva {reserva} excluída.')
        else:
            messages.error(request, f'Reserva {reserva} não encontrada.')
    return redirect('cota365:comissoes_cadastro')


def export_cadastro_pdf(request):
    if not Comissao.objects.exists():
        return HttpResponse('Sem dados.', status=404)

    cliente_filter = request.GET.get('cliente', '').strip()
    imob_filter    = request.GET.get('imob', '').strip()
    status_filter  = request.GET.get('status', 'todas')

    qs = Comissao.objects.order_by('unidade', 'reserva', 'beneficiario')
    if cliente_filter:
        qs = qs.filter(cliente__icontains=cliente_filter)
    if imob_filter:
        qs = qs.filter(imobiliaria__icontains=imob_filter)

    groups = defaultdict(list)
    for c in qs:
        groups[c.reserva].append(c)

    lista = []
    for reserva, records in groups.items():
        first      = records[0]
        extra      = len(records) - 1
        tem_premio = any('premio' in r.tipo_comissao.lower() or
                         'prêmio' in r.tipo_comissao.lower() for r in records)
        extra_str  = f'+{extra}{"P" if tem_premio else ""}' if extra > 0 else ''
        is_cota    = 'COTA EMPREENDIMENTOS' in first.imobiliaria.upper()
        outros_str = ('COTA ' + extra_str if extra_str else 'COTA') if is_cota else extra_str
        total      = sum(r.valor_comissao for r in records)
        dp_prev    = next((r.data_prevista  for r in records if r.data_prevista),  None)
        dp_pago    = next((r.data_pagamento for r in records if r.data_pagamento), None)
        if status_filter == 'nao-pagas' and dp_pago:
            continue
        lista.append({
            'unidade':    first.unidade,
            'reserva':    reserva,
            'cliente':    first.cliente,
            'imobiliaria':first.imobiliaria,
            'total':      total,
            'outros_str': outros_str,
            'tem_premio': tem_premio,
            'dp_prev':    dp_prev,
            'dp_pago':    dp_pago,
        })
    lista.sort(key=lambda x: x['unidade'])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    W = doc.width
    styles = getSampleStyleSheet()

    NAVY   = colors.HexColor('#1a1a2e')
    BORDER = colors.HexColor('#dee2e6')
    GREEN  = colors.HexColor('#d1e7dd')
    YELLOW = colors.HexColor('#fff3cd')
    ORANGE = colors.HexColor('#fff3cd')

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    title_s = ps('CPT', fontSize=14, fontName='Helvetica-Bold', textColor=NAVY, spaceAfter=2)
    sub_s   = ps('CPS', fontSize=8,  textColor=colors.HexColor('#6c757d'), spaceAfter=10)

    def th(txt):
        return Paragraph(f'<b><font color="white">{txt}</font></b>',
                         ps(f'CPTH{txt}', fontSize=7, alignment=1))
    def td(txt):
        return Paragraph(str(txt), ps(f'CPTD{txt}', fontSize=7))
    def tdc(txt):
        return Paragraph(str(txt), ps(f'CPTC{txt}', fontSize=7, alignment=1))
    def tdr(txt):
        return Paragraph(str(txt), ps(f'CPTR{txt}', fontSize=7, alignment=2))
    def tdr_blue(txt):
        return Paragraph(f'<b><font color="#0d6efd">{txt}</font></b>',
                         ps(f'CPLB{txt}', fontSize=7, alignment=2))
    def tdr_green(txt):
        return Paragraph(f'<b><font color="#198754">{txt}</font></b>',
                         ps(f'CPLG{txt}', fontSize=7, alignment=2))

    story = []
    story.append(Paragraph('Cota 365 — Cadastro de Comissões', title_s))
    story.append(Paragraph(
        f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  {len(lista)} reservas',
        sub_s))

    rows = [[th('UNID.'), th('RESERVA'), th('CLIENTE'), th('IMOBILIÁRIA'),
             th('COMISSÃO'), th('OUTRAS'), th('PREVISTA'), th('PAGAMENTO')]]

    row_cmds = [
        ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
        ('GRID',          (0, 0), (-1, -1), 0.3, BORDER),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]

    for i, r in enumerate(lista, 1):
        if r['dp_pago']:
            val_cell = tdr_green(_fmt_brl(r['total']))
        elif r['dp_prev']:
            val_cell = tdr_blue(_fmt_brl(r['total']))
        else:
            val_cell = tdr(_fmt_brl(r['total']))

        rows.append([
            td(r['unidade']),
            td(r['reserva']),
            td(r['cliente'][:30]     if r['cliente']     else ''),
            td(r['imobiliaria'][:28] if r['imobiliaria'] else ''),
            val_cell,
            tdc(r['outros_str']),
            td(r['dp_prev'].strftime('%d/%m/%Y') if r['dp_prev'] else '—'),
            td(r['dp_pago'].strftime('%d/%m/%Y') if r['dp_pago'] else '—'),
        ])
        if r['dp_pago']:
            row_cmds.append(('BACKGROUND', (0, i), (-1, i), GREEN))
        elif r['dp_prev']:
            row_cmds.append(('BACKGROUND', (0, i), (-1, i), YELLOW))

    t = Table(rows,
              colWidths=[W*0.07, W*0.07, W*0.22, W*0.24, W*0.14, W*0.07, W*0.10, W*0.09],
              repeatRows=1)
    t.setStyle(TableStyle(row_cmds))
    story.append(t)

    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="cadastro_comissoes.pdf"'
    return resp


def comissoes(request):
    qs = list(Comissao.objects.all())

    # KPIs — valor_contrato é o mesmo para todos os beneficiários da mesma reserva
    reservas_vt = {}
    for c in qs:
        if c.reserva not in reservas_vt:
            reservas_vt[c.reserva] = c.valor_contrato
    total_vendas   = len(reservas_vt)
    total_contrato = sum(reservas_vt.values())
    total_comissao = sum(c.valor_comissao        for c in qs)
    total_pagar    = sum(c.valor_comissao_pagar  for c in qs)

    # Resumo por Imobiliária (qtde = reservas únicas)
    imob_map      = defaultdict(lambda: {'comissao': 0.0, 'pagar': 0.0})
    imob_reservas = defaultdict(set)
    for c in qs:
        k = c.imobiliaria or '(sem imobiliária)'
        imob_map[k]['comissao'] += c.valor_comissao
        imob_map[k]['pagar']    += c.valor_comissao_pagar
        imob_reservas[k].add(c.reserva)
    resumo_imob = sorted(
        [{'imobiliaria': k, 'n': len(imob_reservas[k]), **v,
          'comissao_fmt': _fmt_brl(v['comissao']),
          'pagar_fmt':    _fmt_brl(v['pagar'])}
         for k, v in imob_map.items()],
        key=lambda x: x['imobiliaria'].lower(),
    )

    # Resumo por Beneficiário
    benef_map = defaultdict(lambda: {'n': 0, 'comissao': 0.0, 'pagar': 0.0})
    for c in qs:
        k = c.beneficiario or '(sem beneficiário)'
        benef_map[k]['n']        += 1
        benef_map[k]['comissao'] += c.valor_comissao
        benef_map[k]['pagar']    += c.valor_comissao_pagar
    resumo_benef = sorted(
        [{'beneficiario': k, **v,
          'comissao_fmt': _fmt_brl(v['comissao']),
          'pagar_fmt':    _fmt_brl(v['pagar'])}
         for k, v in benef_map.items()],
        key=lambda x: x['beneficiario'].lower(),
    )

    # Lista completa
    lista = [{
        'numero':             c.numero,
        'reserva':            c.reserva,
        'unidade':            c.unidade,
        'cliente':            c.cliente,
        'imobiliaria':        c.imobiliaria,
        'beneficiario':       c.beneficiario,
        'tipo_comissao':      c.tipo_comissao,
        'valor_contrato_fmt': _fmt_brl(c.valor_contrato),
        'pct_comissao':       f"{c.pct_comissao:.2f}%".replace('.', ','),
        'valor_comissao_fmt': _fmt_brl(c.valor_comissao),
        'valor_pagar_fmt':    _fmt_brl(c.valor_comissao_pagar),
    } for c in sorted(qs, key=lambda x: (x.unidade, x.beneficiario.lower()))]

    context = {
        'total_n':            total_vendas,
        'total_linhas':       len(qs),
        'total_contrato_fmt': _fmt_brl(total_contrato),
        'total_comissao_fmt': _fmt_brl(total_comissao),
        'total_pagar_fmt':    _fmt_brl(total_pagar),
        'resumo_imob':        resumo_imob,
        'resumo_benef':       resumo_benef,
        'lista':              lista,
    }
    return render(request, 'cota365/comissoes.html', context)


def importar(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo', '')
        arquivo = request.FILES.get('arquivo')
        if not tipo or tipo not in _IMPORTERS:
            messages.error(request, 'Tipo de arquivo inválido.')
            return redirect('cota365:importar')
        if not arquivo:
            messages.error(request, 'Nenhum arquivo selecionado.')
            return redirect('cota365:importar')
        try:
            n, stats = _IMPORTERS[tipo](arquivo, arquivo.name)
            extras = '  |  '.join(f'{k}: {v}' for k, v in stats.items())
            msg = f'{_LABELS[tipo]} importado — {n} registros.'
            if extras:
                msg += f'  ({extras})'
            messages.success(request, msg)
        except Exception as e:
            messages.error(request, f'Erro ao importar {_LABELS[tipo]}: {e}')
        return redirect('cota365:importar')

    # GET — monta status de cada tipo
    ultimos = {}
    for log in ImportLog.objects.all():
        if log.tipo not in ultimos:
            ultimos[log.tipo] = log

    arquivos = []
    for tipo, label in _LABELS.items():
        log = ultimos.get(tipo)
        arquivos.append({
            'tipo':       tipo,
            'label':      label,
            'ultimo':     log.importado_em.strftime('%d/%m/%Y %H:%M') if log else None,
            'registros':  log.total_registros if log else 0,
            'arquivo':    log.nome_arquivo if log else '—',
        })

    from .models import FluxoContrato as FC, Tabela as Tab, Unidade as Un, Venda as Ve
    vgv_tab = sum(t.valor_total for t in Tab.objects.all())
    resumo = {
        'vgv_tabela':  _fmt_brl(vgv_tab),
        'n_contratos': FC.objects.count(),
        'n_unidades':  Un.objects.count(),
        'n_vendas':    Ve.objects.count(),
    }

    from apps.intranet.context_processors import COTA365_TABELAS
    return render(request, 'cota365/importar.html', {
        'arquivos':        arquivos,
        'resumo':          resumo,
        'cota365_tabelas': COTA365_TABELAS,
    })


# ---------------------------------------------------------------------------
# Views principais
# ---------------------------------------------------------------------------

def index(request):
    return render(request, 'cota365/index.html')


def dashboard(request):
    fluxo_rows = _load_fluxo()
    monthly = _build_monthly_totals(fluxo_rows)

    total_geral = sum(monthly.values())
    n_contratos = len(fluxo_rows)
    ticket_medio = total_geral / n_contratos if n_contratos else 0

    top5 = sorted(fluxo_rows, key=lambda x: -x['vgv'])[:5]
    top5_data = [
        {
            'cliente':    r['cliente'],
            'unidade':    r['unidade'],
            'imobiliaria': r['imobiliaria'],
            'vgv_fmt':    _fmt_brl(r['vgv']),
        }
        for r in top5
    ]

    proximos = [
        {
            'mes':        mes,
            'total_fmt':  _fmt_brl(val),
            'total':      round(val, 2),
            'pct':        round(val / total_geral * 100, 1) if total_geral else 0,
        }
        for mes, val in list(monthly.items())[:6]
    ]
    proximos_total = sum(r['total'] for r in proximos)

    resumo_sit, resumo_sit_liquido, resumo_tip, resumo_tip_estoque, preco_medio_tipo, preco_medio_estoque, vgv_tabela, vgv_permuta, vgv_disponivel, vgv_reservada = _compute_resumos_tabela()
    area_priv, area_priv_acess, total_priv, area_comum, area_total = _compute_areas()

    total_vendido = sum(r['vgv'] for r in fluxo_rows)

    ano_totals = defaultdict(float)
    for mes, val in monthly.items():
        ano_totals[mes.split('/')[1]] += val
    receita_por_ano = [
        {
            'ano':        ano,
            'total_fmt':  _fmt_brl(val),
            'pct':        f"{val / total_geral * 100:.1f}%" if total_geral else "0%",
        }
        for ano, val in sorted(ano_totals.items())
    ]

    acumulado = 0.0
    fluxo_mensal_rows = []
    for mes, val in monthly.items():
        acumulado += val
        fluxo_mensal_rows.append({
            'mes':           mes,
            'total_fmt':     _fmt_brl(val),
            'acumulado_fmt': _fmt_brl(acumulado),
        })

    vgv_liquido = vgv_tabela - vgv_permuta

    context = {
        'total_geral':      _fmt_brl(vgv_tabela),
        'vgv_liquido':      _fmt_brl(vgv_liquido),
        'n_contratos':      n_contratos,
        'ticket_medio':     _fmt_brl(ticket_medio),
        'total_vendido':    _fmt_brl(total_vendido),
        'area_priv':        _fmt_m2(area_priv),
        'area_priv_acess':  _fmt_m2(area_priv_acess),
        'total_priv':       _fmt_m2(total_priv),
        'area_comum':       _fmt_m2(area_comum),
        'area_total':       _fmt_m2(area_total),
        'resumo_sit':            resumo_sit,
        'resumo_sit_liquido':    resumo_sit_liquido,
        'resumo_tip':            resumo_tip,
        'resumo_tip_estoque':    resumo_tip_estoque,
        'preco_medio_tipo':      preco_medio_tipo,
        'preco_medio_estoque':   preco_medio_estoque,
        'receita_por_ano':  receita_por_ano,
        'total_fluxo_fmt':  _fmt_brl(total_geral),
        'fluxo_mensal_rows': fluxo_mensal_rows,
        'top5':             top5_data,
        'proximos':         proximos,
    }
    return render(request, 'cota365/dashboard.html', context)


def export_dashboard(request):
    from reportlab.platypus import HRFlowable

    fluxo_rows = _load_fluxo()
    monthly = _build_monthly_totals(fluxo_rows)
    total_fluxo = sum(monthly.values())
    n_contratos = len(fluxo_rows)
    ticket_medio = total_fluxo / n_contratos if n_contratos else 0
    total_vendido = sum(r['vgv'] for r in fluxo_rows)

    resumo_sit, resumo_sit_liquido, resumo_tip, resumo_tip_estoque, preco_medio_tipo, preco_medio_estoque, vgv_tabela, vgv_permuta, vgv_disponivel, vgv_reservada = _compute_resumos_tabela()
    area_priv, area_priv_acess, total_priv, area_comum, area_total = _compute_areas()

    ano_totals = defaultdict(float)
    for mes, val in monthly.items():
        ano_totals[mes.split('/')[1]] += val

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    W = doc.width

    styles = getSampleStyleSheet()
    NAVY   = colors.HexColor('#1a1a2e')
    LIGHT  = colors.HexColor('#f8f9fa')
    TOTAL_BG = colors.HexColor('#e9ecef')
    BORDER = colors.HexColor('#dee2e6')

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    title_s = ps('T',  fontSize=16, textColor=NAVY, fontName='Helvetica-Bold', spaceAfter=6)
    sub_s   = ps('S',  fontSize=8,  textColor=colors.HexColor('#6c757d'), spaceAfter=14)
    sec_s   = ps('H',  fontSize=9,  textColor=NAVY, fontName='Helvetica-Bold', spaceBefore=12, spaceAfter=5)
    cell_s  = ps('C',  fontSize=8,  leading=11)
    cell_r  = ps('CR', fontSize=8,  leading=11, alignment=2)
    cell_b  = ps('CB', fontSize=8,  leading=11, fontName='Helvetica-Bold')
    cell_rb = ps('CRB',fontSize=8,  leading=11, fontName='Helvetica-Bold', alignment=2)
    cell_c  = ps('CC', fontSize=8,  leading=11, alignment=1)

    def th(txt):
        return Paragraph(txt, ps('TH', fontSize=8, fontName='Helvetica-Bold',
                                  textColor=colors.white, alignment=1))
    def td(txt):   return Paragraph(str(txt), cell_s)
    def tdr(txt):  return Paragraph(str(txt), cell_r)
    def tdb(txt):  return Paragraph(str(txt), cell_b)
    def tdrb(txt): return Paragraph(str(txt), cell_rb)
    def tdc(txt):  return Paragraph(str(txt), cell_c)

    def tbl(data, col_widths, total_last=False):
        t = Table(data, colWidths=col_widths, repeatRows=1)
        cmds = [
            ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, LIGHT]),
            ('GRID',          (0, 0), (-1, -1), 0.4, BORDER),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]
        if total_last:
            cmds += [
                ('BACKGROUND', (0, -1), (-1, -1), TOTAL_BG),
                ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]
        t.setStyle(TableStyle(cmds))
        return t

    story = []
    story.append(Paragraph('Cota 365 — Resumo Gerencial', title_s))
    story.append(Paragraph(
        f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  {n_contratos} contratos', sub_s))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER, spaceAfter=10))

    story.append(Paragraph('Áreas', sec_s))
    story.append(tbl([[
        th('ÁREA PRIVATIVA'), th('ÁREA PRIV. ACESSÓRIA'), th('TOTAL ÁREA PRIVATIVA'),
        th('ÁREA COMUM'), th('ÁREA TOTAL'),
    ], [
        tdc(_fmt_m2(area_priv)), tdc(_fmt_m2(area_priv_acess)), tdc(_fmt_m2(total_priv)),
        tdc(_fmt_m2(area_comum)), tdc(_fmt_m2(area_total)),
    ]], [W/5]*5))
    story.append(Spacer(1, 6))

    vgv_liquido    = vgv_tabela - vgv_permuta
    total_real_a   = vgv_disponivel + vgv_reservada + total_vendido + vgv_permuta
    total_real_b   = vgv_disponivel + vgv_reservada + total_vendido

    def _lbl(txt):
        return Paragraph(txt, ps('LB', fontSize=7, textColor=colors.HexColor('#6c757d'),
                                  fontName='Helvetica-Oblique', alignment=1))

    story.append(Paragraph('Indicadores Gerais', sec_s))
    kpi_table = Table([
        [th('VGV TOTAL'), th('VGV LÍQUIDO'), th('CONTRATOS'), th('TICKET MÉDIO'), th('TOTAL VENDIDO')],
        [tdrb(_fmt_brl(vgv_tabela)), tdrb(_fmt_brl(vgv_liquido)),
         tdrb(str(n_contratos)),     tdrb(_fmt_brl(ticket_medio)), tdrb(_fmt_brl(total_vendido))],
        [tdrb(_fmt_brl(total_real_a)), tdrb(_fmt_brl(total_real_b)),
         _lbl('—'), _lbl('—'), _lbl('—')],
    ], colWidths=[W/5]*5)
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ('BACKGROUND',    (0, 2), (-1, 2), colors.HexColor('#e8f0fe')),
        ('FONTNAME',      (0, 2), (-1, 2), 'Helvetica-Bold'),
    ]))
    story.append(kpi_table)

    legend_style = ps('LEG', fontSize=7, textColor=colors.HexColor('#6c757d'), spaceBefore=3, spaceAfter=6)
    story.append(Paragraph(
        '<b>Linha 1:</b> valores de tabela de vendas  |  <b>Linha 2:</b> valores reais de vendas (contratos)',
        legend_style,
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph('Resumo por Situação (Com permutas)', sec_s))
    sit_header = [[
        th('SITUAÇÃO'), th('VALOR TABELA'), th('% VALOR'),
        th('ÁREA PRIV.'), th('% ÁREA'), th('UNIDADES'), th('% UNID.'),
    ]]
    sit_rows = [
        [td(r['situacao']), tdr(r['vt_fmt']), tdr(r['pct_vt']),
         tdr(r['ap_fmt']),  tdr(r['pct_ap']), tdr(str(r['n'])), tdr(r['pct_n'])]
        for r in resumo_sit
    ]
    story.append(tbl(sit_header + sit_rows,
                     [3*cm, 3.5*cm, 1.8*cm, 3*cm, 1.8*cm, 1.8*cm, 1.8*cm], total_last=True))
    story.append(Spacer(1, 6))

    story.append(Paragraph('Resumo por Situação (Sem permutas)', sec_s))
    liq_header = [[
        th('SITUAÇÃO'), th('VALOR TABELA'), th('% VALOR'),
        th('ÁREA PRIV.'), th('% ÁREA'), th('UNIDADES'), th('% UNID.'),
    ]]
    liq_rows = [
        [td(r['situacao']), tdr(r['vt_fmt']), tdr(r['pct_vt']),
         tdr(r['ap_fmt']),  tdr(r['pct_ap']), tdr(str(r['n'])), tdr(r['pct_n'])]
        for r in resumo_sit_liquido
    ]
    story.append(tbl(liq_header + liq_rows,
                     [3*cm, 3.5*cm, 1.8*cm, 3*cm, 1.8*cm, 1.8*cm, 1.8*cm], total_last=True))
    story.append(Spacer(1, 6))

    story.append(Paragraph('Resumo por Tipo', sec_s))
    tip_header = [[th('QTDE'), th('TIPO'), th('M² PRIV.'), th('VALOR TABELA'), th('R$/M²')]]
    tip_rows = [
        [tdr(str(r['n'])), td(r['tipo']), tdr(r['ap_fmt']), tdr(r['vt_fmt']), tdr(r['rsm2'])]
        for r in resumo_tip
    ]
    story.append(tbl(tip_header + tip_rows, [1.5*cm, 3.5*cm, 3*cm, 4.5*cm, 4.2*cm], total_last=True))
    story.append(Paragraph(
        f'Preço médio por unidade: {preco_medio_tipo}',
        ps('PM', fontSize=8, textColor=NAVY, fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=6),
    ))

    story.append(PageBreak())
    story.append(Paragraph('Resumo por Tipo (Estoque)', sec_s))
    est_header = [[th('QTDE'), th('TIPO'), th('M² PRIV.'), th('VALOR TABELA'), th('R$/M²')]]
    est_rows = [
        [tdr(str(r['n'])), td(r['tipo']), tdr(r['ap_fmt']), tdr(r['vt_fmt']), tdr(r['rsm2'])]
        for r in resumo_tip_estoque
    ]
    story.append(tbl(est_header + est_rows, [1.5*cm, 3.5*cm, 3*cm, 4.5*cm, 4.2*cm], total_last=True))
    story.append(Paragraph(
        f'Preço médio por unidade (estoque): {preco_medio_estoque}',
        ps('PM', fontSize=8, textColor=NAVY, fontName='Helvetica-Bold', spaceBefore=4, spaceAfter=6),
    ))

    story.append(Paragraph('Receita por Ano', sec_s))
    ano_header = [[th('ANO'), th('RECEITA PREVISTA'), th('% DO TOTAL')]]
    ano_rows = [
        [td(ano), tdr(_fmt_brl(val)),
         tdr(f'{val/total_fluxo*100:.1f}%' if total_fluxo else '0%')]
        for ano, val in sorted(ano_totals.items())
    ]
    ano_rows.append([tdb('TOTAL'), tdrb(_fmt_brl(total_fluxo)), tdrb('100%')])
    story.append(tbl(ano_header + ano_rows, [3*cm, 7*cm, 4*cm], total_last=True))
    story.append(Spacer(1, 6))

    story.append(Paragraph('Fluxo de Caixa Mensal Completo', sec_s))
    fm_header = [[th('MÊS'), th('RECEBIMENTO'), th('ACUMULADO')]]
    fm_rows = []
    acumulado = 0.0
    for mes, val in monthly.items():
        acumulado += val
        fm_rows.append([td(mes), tdr(_fmt_brl(val)), tdr(_fmt_brl(acumulado))])
    fm_rows.append([tdb('TOTAL'), tdrb(_fmt_brl(total_fluxo)), tdrb('')])
    story.append(tbl(fm_header + fm_rows, [3*cm, 7*cm, 6.5*cm], total_last=True))

    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="resumo_cota365.pdf"'
    return resp


def unidades(request):
    headers, rows = _load_unidades()

    status_col = next((i for i, h in enumerate(headers) if h.lower() == 'status'), None)
    tabela_col = next((i for i, h in enumerate(headers) if 'tabela' in h.lower()), None)
    venda_col  = next((i for i, h in enumerate(headers) if 'venda'  in h.lower()), None)

    def _col(name):
        return next((i for i, h in enumerate(headers)
                     if h.lower().replace('.', '').replace(' ', '') ==
                     name.lower().replace('.', '').replace(' ', '')), None)

    ap_col  = _col('Area Privativa')
    apa_col = _col('Area Priv Acessoria')
    ac_col  = _col('Area Comum')

    def _area(row, idx):
        if idx is None: return 0.0
        try: return float(row[idx]) if row[idx] not in ('', None) else 0.0
        except (ValueError, TypeError): return 0.0

    total       = len(rows)
    vendidos    = sum(1 for r in rows if status_col is not None and str(r[status_col]).lower() == 'vendido')
    disponiveis = sum(1 for r in rows if status_col is not None and str(r[status_col]).lower() == 'disponível')
    permutas_n  = sum(1 for r in rows if status_col is not None and str(r[status_col]).lower() == 'permuta')
    reservados  = total - vendidos - disponiveis - permutas_n

    def _to_float(v):
        try: return float(v)
        except (ValueError, TypeError): return 0.0

    vgv_vendido = sum(
        _to_float(r[venda_col]) for r in rows
        if venda_col is not None and status_col is not None
        and str(r[status_col]).lower() == 'vendido'
    ) if venda_col is not None else 0

    vgv_disponivel = sum(
        _to_float(r[tabela_col]) for r in rows
        if tabela_col is not None and status_col is not None
        and str(r[status_col]).lower() == 'disponível'
    ) if tabela_col is not None else 0

    area_priv       = sum(_area(r, ap_col)  for r in rows)
    area_priv_acess = sum(_area(r, apa_col) for r in rows)
    area_comum      = sum(_area(r, ac_col)  for r in rows)
    total_priv      = area_priv + area_priv_acess
    area_total      = total_priv + area_comum

    STATUS_CSS = {
        'vendido':    'badge-vendido',
        'disponível': 'badge-disponivel',
        'reservado':  'badge-reservado',
        'permuta':    'badge-permuta',
    }

    def make_cells(row):
        cells = []
        for i, v in enumerate(row):
            h = headers[i].lower()
            if ('tabela' in h or 'venda' in h) and v not in ('', 0, None):
                cells.append({'val': _fmt_brl(float(v)), 'cls': 'text-end fw-semibold', 'badge': ''})
            elif h == 'status':
                badge = STATUS_CSS.get(str(v).lower(), '')
                cells.append({'val': v, 'cls': 'text-center', 'badge': badge})
            else:
                cells.append({'val': v, 'cls': '', 'badge': ''})
        return cells

    context = {
        'headers':        headers,
        'rows':           [make_cells(r) for r in rows],
        'total':          total,
        'vendidos':       vendidos,
        'disponiveis':    disponiveis,
        'reservados':     reservados,
        'permutas_n':     permutas_n,
        'vgv_vendido':    _fmt_brl(vgv_vendido),
        'vgv_disponivel': _fmt_brl(vgv_disponivel),
        'area_priv':      _fmt_m2(area_priv),
        'area_priv_acess': _fmt_m2(area_priv_acess),
        'total_priv':     _fmt_m2(total_priv),
        'area_comum':     _fmt_m2(area_comum),
        'area_total':     _fmt_m2(area_total),
    }
    return render(request, 'cota365/unidades.html', context)


def export_unidades(request):
    fmt = request.GET.get('format', 'xlsx')
    headers, rows = _load_unidades()
    price_cols = {i for i, h in enumerate(headers) if 'tabela' in h.lower() or 'venda' in h.lower()}
    if fmt == 'pdf':
        return _export_unidades_pdf(headers, rows, price_cols)
    return _export_unidades_xlsx(headers, rows, price_cols)


def vendas(request):
    vendas_rows = _load_vendas()
    fluxo_rows  = _load_fluxo()
    fluxo_by_id = {r['id']: r for r in fluxo_rows}
    vinculos    = _load_vinculos()

    contracts = []
    total_geral = 0.0
    for v in vendas_rows:
        f = fluxo_by_id.get(v['numero'], {})
        valor = f.get('vgv', 0) or f.get('pv', 0)
        status = 'VENDIDO' if 'Vend' in v['situacao'] else v['situacao'].upper()
        vinc = vinculos.get(v['unidade'], {})
        contracts.append({
            'numero':        f"#{v['numero']}",
            'cliente':       v['cliente'],
            'empreendimento': f.get('empreendimento', 'Cota 365'),
            'unidade':       v['unidade'],
            'status':        status,
            'valor':         valor,
            'valor_fmt':     _fmt_brl(valor),
            'garagens':      vinc.get('garagens', ''),
            'hb':            vinc.get('hb', ''),
        })
        total_geral += valor

    contracts.sort(key=lambda x: x['cliente'])
    context = {
        'contracts':   contracts,
        'total_geral': _fmt_brl(total_geral),
        'n_contratos': len(contracts),
    }
    return render(request, 'cota365/vendas.html', context)


def fluxo_mensal(request):
    fluxo_rows = _load_fluxo()
    monthly    = _build_monthly_totals(fluxo_rows)

    total_geral = sum(monthly.values())
    acumulado   = 0.0
    rows = []
    for mes, val in monthly.items():
        acumulado += val
        rows.append({'mes': mes, 'total': val, 'total_fmt': _fmt_brl(val),
                     'acumulado_fmt': _fmt_brl(acumulado)})

    context = {
        'rows':        rows,
        'total_geral': _fmt_brl(total_geral),
        'n_contratos': len(fluxo_rows),
    }
    return render(request, 'cota365/fluxo.html', context)


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def export_vendas(request):
    fmt = request.GET.get('format', 'xlsx')
    vendas_rows = _load_vendas()
    fluxo_rows  = _load_fluxo()
    fluxo_by_id = {r['id']: r for r in fluxo_rows}
    vinculos    = _load_vinculos()

    contracts = []
    total_geral = 0.0
    for v in vendas_rows:
        f = fluxo_by_id.get(v['numero'], {})
        valor = f.get('vgv', 0) or f.get('pv', 0)
        status = 'VENDIDO' if 'Vend' in v['situacao'] else v['situacao'].upper()
        vinc = vinculos.get(v['unidade'], {})
        contracts.append({
            'numero':        f"#{v['numero']}",
            'cliente':       v['cliente'],
            'empreendimento': f.get('empreendimento', 'Cota 365'),
            'unidade':       v['unidade'],
            'status':        status,
            'valor':         valor,
            'garagens':      vinc.get('garagens', ''),
            'hb':            vinc.get('hb', ''),
        })
        total_geral += valor
    contracts.sort(key=lambda x: x['cliente'].lower())

    if fmt == 'pdf':
        return _export_vendas_pdf(contracts, total_geral)
    return _export_vendas_xlsx(contracts, total_geral)


def export_fluxo(request):
    fmt = request.GET.get('format', 'xlsx')
    fluxo_rows  = _load_fluxo()
    monthly     = _build_monthly_totals(fluxo_rows)
    total_geral = sum(monthly.values())
    rows = [{'mes': mes, 'total': val} for mes, val in monthly.items()]

    if fmt == 'pdf':
        return _export_fluxo_pdf(rows, total_geral)
    return _export_fluxo_xlsx(rows, total_geral)


# -- Excel helpers -----------------------------------------------------------

_HEADER_FILL = PatternFill('solid', fgColor='1a1a2e')
_HEADER_FONT = Font(color='FFFFFF', bold=True)
_STATUS_FILL = PatternFill('solid', fgColor='d4edda')
_STATUS_FONT = Font(color='155724', bold=True)
_ALT_FILL    = PatternFill('solid', fgColor='f8f9fa')
_TOTAL_FILL  = PatternFill('solid', fgColor='e9ecef')
_BOLD        = Font(bold=True)


def _thin_border():
    s = Side(style='thin', color='dee2e6')
    return Border(left=s, right=s, top=s, bottom=s)


def _export_unidades_xlsx(headers, rows, price_cols):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Unidades'

    ws.merge_cells(f'A1:{get_column_letter(len(headers))}1')
    ws['A1'] = 'Cota 365 — Cadastro de Unidades'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=3, column=col, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = _thin_border()
        ws.column_dimensions[get_column_letter(col)].width = max(14, len(str(h)) + 4)

    status_col = next((i for i, h in enumerate(headers) if h.lower() == 'status'), None)
    STATUS_COLORS = {
        'vendido':    ('d4edda', '155724'),
        'disponível': ('d1ecf1', '0c5460'),
        'reservado':  ('fff3cd', '856404'),
        'permuta':    ('f3e8ff', '5a1e96'),
    }

    for i, row in enumerate(rows):
        r = 4 + i
        fill = _ALT_FILL if i % 2 == 0 else PatternFill()
        for col, val in enumerate(row, 1):
            cell = ws.cell(row=r, column=col, value=val)
            cell.border = _thin_border()
            if col - 1 in price_cols and val not in ('', 0, None):
                cell.number_format = '"R$ "#,##0.00'
                cell.alignment = Alignment(horizontal='right')
                cell.value = float(val) if val else 0
            elif col - 1 == status_col and val:
                cp = STATUS_COLORS.get(str(val).lower(), ('', ''))
                if cp[0]:
                    cell.fill = PatternFill('solid', fgColor=cp[0])
                    cell.font = Font(color=cp[1], bold=True)
                    cell.alignment = Alignment(horizontal='center')
            else:
                cell.fill = fill

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="unidades_cota365.xlsx"'
    return resp


def _export_unidades_pdf(headers, rows, price_cols):
    buf = io.BytesIO()
    page = landscape(A4) if len(headers) > 6 else A4
    doc = SimpleDocTemplate(buf, pagesize=page,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    title_s = ParagraphStyle('t', parent=styles['Heading1'], fontSize=13, spaceAfter=6)
    sub_s   = ParagraphStyle('s', parent=styles['Normal'],  fontSize=9,  spaceAfter=14,
                              textColor=colors.HexColor('#6c757d'))

    story = [
        Paragraph('Cota 365 — Cadastro de Unidades', title_s),
        Paragraph(f'Total de unidades: {len(rows)}  |  Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}', sub_s),
    ]

    base_w    = doc.width / len(headers)
    first_w   = base_w * 0.6
    remaining = (doc.width - first_w) / (len(headers) - 1) if len(headers) > 1 else base_w
    tabela_idx = next((i for i, h in enumerate(headers) if 'tabela' in h.lower()), None)
    venda_idx  = next((i for i, h in enumerate(headers) if 'venda'  in h.lower()), None)
    wide_cols  = {i for i in (tabela_idx, venda_idx) if i is not None}
    total_extra = remaining * 0.15 * len(wide_cols)
    n_other = len(headers) - 1 - len(wide_cols)
    shrink = total_extra / n_other if n_other > 0 else 0
    col_widths = []
    for i in range(len(headers)):
        if i == 0:          col_widths.append(first_w)
        elif i in wide_cols: col_widths.append(remaining * 1.15)
        else:               col_widths.append(remaining - shrink)

    HEADER_LABELS = {'Complemento do Tipo': 'Compl. do Tipo'}
    header_row = [
        Paragraph(f'<b><font color="white">{HEADER_LABELS.get(h, h)}</font></b>',
                  ParagraphStyle('th', parent=styles['Normal'], fontSize=7, alignment=1))
        for h in headers
    ]
    data = [header_row]
    for row in rows:
        pdf_row = []
        for i, val in enumerate(row):
            if i in price_cols and val not in ('', None, 0):
                txt = _fmt_brl(float(val))
                pdf_row.append(Paragraph(txt, ParagraphStyle('cr', parent=styles['Normal'], fontSize=7, alignment=2)))
            else:
                pdf_row.append(Paragraph(str(val) if val is not None else '',
                                         ParagraphStyle('c', parent=styles['Normal'], fontSize=7)))
        data.append(pdf_row)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('GRID',          (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('TOPPADDING',    (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="unidades_cota365.pdf"'
    return resp


def _export_vendas_xlsx(contracts, total_geral):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Unidades Vendidas'

    ws.merge_cells('A1:H1')
    ws['A1'] = 'Cota 365 — Unidades Vendidas'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:H2')
    ws['A2'] = f'Total de Contratos: {len(contracts)}    |    Total Geral: {_fmt_brl(total_geral)}'
    ws['A2'].alignment = Alignment(horizontal='center')
    ws['A2'].font = Font(bold=True)

    headers = ['Nº', 'CLIENTE', 'EMPREENDIMENTO', 'UNIDADE', 'GARAGENS', 'HB', 'STATUS', 'TOTAL CONTRATO']
    widths  = [8, 38, 16, 12, 14, 10, 12, 22]
    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = _thin_border()
        ws.column_dimensions[get_column_letter(col)].width = w

    for i, c in enumerate(contracts):
        row = 5 + i
        fill = _ALT_FILL if i % 2 == 0 else PatternFill()
        data = [c['numero'], c['cliente'], c['empreendimento'], c['unidade'],
                c['garagens'], c['hb'], c['status'], c['valor']]
        for col, val in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = _thin_border()
            if col not in (7, 8): cell.fill = fill
            if col == 8:
                cell.number_format = '"R$ "#,##0.00'
                cell.alignment = Alignment(horizontal='right')
            if col == 7:
                cell.fill = _STATUS_FILL
                cell.font = _STATUS_FONT
                cell.alignment = Alignment(horizontal='center')

    total_row = 5 + len(contracts)
    ws.cell(row=total_row, column=7, value='TOTAL GERAL').font = _BOLD
    ws.cell(row=total_row, column=7).fill = _TOTAL_FILL
    ws.cell(row=total_row, column=7).alignment = Alignment(horizontal='center')
    ws.cell(row=total_row, column=8, value=total_geral).number_format = '"R$ "#,##0.00'
    ws.cell(row=total_row, column=8).font = _BOLD
    ws.cell(row=total_row, column=8).fill = _TOTAL_FILL
    ws.cell(row=total_row, column=8).alignment = Alignment(horizontal='right')

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="unidades_vendidas.xlsx"'
    return resp


def _export_fluxo_xlsx(rows, total_geral):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Fluxo Mensal'

    ws.merge_cells('A1:C1')
    ws['A1'] = 'Cota 365 — Fluxo Mensal de Receitas'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')

    ws.merge_cells('A2:C2')
    ws['A2'] = f'Total Geral: {_fmt_brl(total_geral)}'
    ws['A2'].alignment = Alignment(horizontal='center')
    ws['A2'].font = Font(bold=True)

    headers = ['MÊS', 'TOTAL MÊS', 'ACUMULADO']
    widths  = [16, 24, 24]
    for col, (h, w) in enumerate(zip(headers, widths), 1):
        cell = ws.cell(row=4, column=col, value=h)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = _thin_border()
        ws.column_dimensions[get_column_letter(col)].width = w

    acumulado = 0.0
    for i, r in enumerate(rows):
        row = 5 + i
        acumulado += r['total']
        fill = _ALT_FILL if i % 2 == 0 else PatternFill()
        for col, val in enumerate([r['mes'], r['total'], acumulado], 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = _thin_border()
            cell.fill = fill
            if col > 1:
                cell.number_format = '"R$ "#,##0.00'
                cell.alignment = Alignment(horizontal='right')

    total_row = 5 + len(rows)
    ws.cell(row=total_row, column=1, value='Total por Série').font = _BOLD
    ws.cell(row=total_row, column=1).fill = _TOTAL_FILL
    ws.cell(row=total_row, column=2, value=total_geral).number_format = '"R$ "#,##0.00'
    ws.cell(row=total_row, column=2).font = _BOLD
    ws.cell(row=total_row, column=2).fill = _TOTAL_FILL
    ws.cell(row=total_row, column=2).alignment = Alignment(horizontal='right')

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="fluxo_mensal.xlsx"'
    return resp


def _export_vendas_pdf(contracts, total_geral):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph('Cota 365 — Unidades Vendidas',
                  ParagraphStyle('title', parent=styles['Heading1'], fontSize=14, spaceAfter=4)),
        Paragraph(f'Nº de Contratos: {len(contracts)}    |    Total Geral: {_fmt_brl(total_geral)}',
                  ParagraphStyle('sub', parent=styles['Normal'], fontSize=10, spaceAfter=12)),
    ]

    header = ['Nº', 'CLIENTE', 'EMPREENDIMENTO', 'UNIDADE', 'GARAGENS', 'HB', 'STATUS', 'TOTAL CONTRATO']
    data = [header]
    for c in contracts:
        data.append([c['numero'], c['cliente'], c['empreendimento'],
                     c['unidade'], c['garagens'], c['hb'], c['status'], _fmt_brl(c['valor'])])
    data.append(['', '', '', '', '', '', 'TOTAL GERAL', _fmt_brl(total_geral)])

    t = Table(data, colWidths=[1.2*cm, 7*cm, 3.5*cm, 2.5*cm, 2.5*cm, 1.8*cm, 2.2*cm, 3.8*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 8),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN',         (1, 1), (1, -2),  'LEFT'),
        ('ALIGN',         (7, 1), (7, -1),  'RIGHT'),
        ('FONTSIZE',      (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS',(0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
        ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="unidades_vendidas.pdf"'
    return resp


def _export_fluxo_pdf(rows, total_geral):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph('Cota 365 — Fluxo Mensal de Receitas',
                  ParagraphStyle('title', parent=styles['Heading1'], fontSize=14, spaceAfter=4)),
        Paragraph(f'Total Geral: {_fmt_brl(total_geral)}',
                  ParagraphStyle('sub', parent=styles['Normal'], fontSize=10, spaceAfter=12)),
    ]

    data = [['MÊS', 'TOTAL MÊS', 'ACUMULADO']]
    acumulado = 0.0
    for r in rows:
        acumulado += r['total']
        data.append([r['mes'], _fmt_brl(r['total']), _fmt_brl(acumulado)])
    data.append(['Total por Série', _fmt_brl(total_geral), ''])

    t = Table(data, colWidths=[4*cm, 7*cm, 7*cm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, 0), 9),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN',         (1, 1), (-1, -1), 'RIGHT'),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS',(0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ('BACKGROUND',    (0, -1), (-1, -1), colors.HexColor('#e9ecef')),
        ('FONTNAME',      (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="fluxo_mensal.pdf"'
    return resp


# ---------------------------------------------------------------------------
# Comparativo de Áreas — Tabela × Unidades
# ---------------------------------------------------------------------------

def export_areas_comparativo(request):
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    HDR_FILL  = PatternFill('solid', fgColor='1A1A2E')
    HDR_FONT  = Font(bold=True, color='FFFFFF', size=10)
    DIFF_FILL = PatternFill('solid', fgColor='FFE0E0')
    OK_FILL   = PatternFill('solid', fgColor='E0F4E0')
    ONLY_FILL = PatternFill('solid', fgColor='FFF3CD')
    TOTAL_FONT = Font(bold=True, size=10)
    BORDER = Border(
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC'),
    )

    def _hdr(ws, row, cols):
        for c, txt in enumerate(cols, 1):
            cell = ws.cell(row=row, column=c, value=txt)
            cell.font  = HDR_FONT
            cell.fill  = HDR_FILL
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = BORDER

    def _auto_width(ws):
        for col in ws.columns:
            max_len = max((len(str(c.value or '')) for c in col), default=8)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 30)

    wb = openpyxl.Workbook()

    # ── Aba 1: Tabela ─────────────────────────────────────────────────────────
    ws_tab = wb.active
    ws_tab.title = 'Tabela'
    _hdr(ws_tab, 1, ['UNIDADE', 'TIPOLOGIA', 'SITUAÇÃO', 'ÁREA PRIV. (m²)', 'VALOR TOTAL'])
    ws_tab.row_dimensions[1].height = 28
    for i, t in enumerate(Tabela.objects.order_by('unidade'), 2):
        row = [t.unidade, t.tipologia, t.situacao, t.area_privativa, t.valor_total]
        for c, val in enumerate(row, 1):
            cell = ws_tab.cell(row=i, column=c, value=val)
            cell.border = BORDER
            if c in (4, 5):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
    # total
    n = Tabela.objects.count()
    total_row = n + 2
    ws_tab.cell(row=total_row, column=1, value='TOTAL').font = TOTAL_FONT
    ws_tab.cell(row=total_row, column=4,
                value=sum(t.area_privativa for t in Tabela.objects.all())).number_format = '#,##0.00'
    ws_tab.cell(row=total_row, column=4).font = TOTAL_FONT
    ws_tab.cell(row=total_row, column=5,
                value=sum(t.valor_total for t in Tabela.objects.all())).number_format = '#,##0.00'
    ws_tab.cell(row=total_row, column=5).font = TOTAL_FONT
    _auto_width(ws_tab)

    # ── Aba 2: Unidades ───────────────────────────────────────────────────────
    ws_uni = wb.create_sheet('Unidades')
    _hdr(ws_uni, 1, ['UNIDADE', 'TIPO', 'COMPLEMENTO', 'ÁREA PRIV. (m²)',
                     'ÁREA PRIV. ACESS. (m²)', 'ÁREA COMUM (m²)', 'TOTAL PRIV. (m²)', 'FRAÇÃO IDEAL'])
    ws_uni.row_dimensions[1].height = 28
    for i, u in enumerate(Unidade.objects.order_by('unidade'), 2):
        total_priv = u.area_privativa + u.area_priv_acessoria
        row = [u.unidade, u.tipo, u.complemento_tipo, u.area_privativa,
               u.area_priv_acessoria, u.area_comum, total_priv, u.fracao_ideal]
        for c, val in enumerate(row, 1):
            cell = ws_uni.cell(row=i, column=c, value=val)
            cell.border = BORDER
            if c in (4, 5, 6, 7):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
    n2 = Unidade.objects.count()
    total_row2 = n2 + 2
    ws_uni.cell(row=total_row2, column=1, value='TOTAL').font = TOTAL_FONT
    for col, attr in [(4, 'area_privativa'), (5, 'area_priv_acessoria'), (6, 'area_comum')]:
        val = sum(getattr(u, attr) for u in Unidade.objects.all())
        c = ws_uni.cell(row=total_row2, column=col, value=val)
        c.number_format = '#,##0.00'
        c.font = TOTAL_FONT
    tp = sum(u.area_privativa + u.area_priv_acessoria for u in Unidade.objects.all())
    c7 = ws_uni.cell(row=total_row2, column=7, value=tp)
    c7.number_format = '#,##0.00'
    c7.font = TOTAL_FONT
    _auto_width(ws_uni)

    # ── Aba 3: Comparativo ────────────────────────────────────────────────────
    ws_cmp = wb.create_sheet('Comparativo')
    _hdr(ws_cmp, 1, [
        'UNIDADE',
        'SITUAÇÃO (Tab.)', 'ÁREA PRIV. Tabela (m²)',
        'ÁREA PRIV. Unidade (m²)', 'ÁREA PRIV. ACESS. (m²)', 'TOTAL PRIV. Unid. (m²)',
        'DIFERENÇA (Tab − Unid)',
        'STATUS',
    ])
    ws_cmp.row_dimensions[1].height = 28

    tab_map  = {t.unidade: t for t in Tabela.objects.all()}
    uni_map  = {u.unidade: u for u in Unidade.objects.all()}
    all_keys = sorted(set(tab_map) | set(uni_map))

    diff_count = 0
    for i, key in enumerate(all_keys, 2):
        t = tab_map.get(key)
        u = uni_map.get(key)

        ap_tab  = t.area_privativa if t else None
        sit_tab = t.situacao       if t else None
        ap_uni  = u.area_privativa      if u else None
        apa_uni = u.area_priv_acessoria if u else None
        tp_uni  = (ap_uni + apa_uni)    if u else None

        if t and u:
            diff  = round(ap_tab - ap_uni, 4)
            status = 'OK' if diff == 0 else f'DIVERGE {diff:+.4f}'
            fill   = OK_FILL if diff == 0 else DIFF_FILL
            if diff != 0:
                diff_count += 1
        elif t:
            diff   = None
            status = 'Só na Tabela'
            fill   = ONLY_FILL
        else:
            diff   = None
            status = 'Só em Unidades'
            fill   = ONLY_FILL

        row_vals = [key, sit_tab, ap_tab, ap_uni, apa_uni, tp_uni, diff, status]
        for c, val in enumerate(row_vals, 1):
            cell = ws_cmp.cell(row=i, column=c, value=val)
            cell.border = BORDER
            cell.fill   = fill
            if c in (3, 4, 5, 6, 7) and val is not None:
                cell.number_format = '#,##0.0000'
                cell.alignment = Alignment(horizontal='right')

    # totais comparativo
    tr = len(all_keys) + 2
    ws_cmp.cell(row=tr, column=1, value='TOTAL').font = TOTAL_FONT
    for col, vals in [
        (3, [t.area_privativa for t in tab_map.values()]),
        (4, [u.area_privativa for u in uni_map.values()]),
        (5, [u.area_priv_acessoria for u in uni_map.values()]),
        (6, [u.area_privativa + u.area_priv_acessoria for u in uni_map.values()]),
    ]:
        c = ws_cmp.cell(row=tr, column=col, value=sum(vals))
        c.number_format = '#,##0.0000'
        c.font = TOTAL_FONT

    ws_cmp.cell(row=tr + 1, column=1,
                value=f'Unidades com divergência: {diff_count}').font = Font(bold=True, color='CC0000')

    _auto_width(ws_cmp)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="comparativo_areas_cota365.xlsx"'
    return resp


# ---------------------------------------------------------------------------
# Comissões — exportações
# ---------------------------------------------------------------------------

def export_comissoes_excel(request):
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    HDR_FILL  = PatternFill('solid', fgColor='1A1A2E')
    HDR_FONT  = Font(bold=True, color='FFFFFF', size=10)
    BORDER    = Border(
        left=Side(style='thin', color='CCCCCC'), right=Side(style='thin', color='CCCCCC'),
        top=Side(style='thin', color='CCCCCC'),  bottom=Side(style='thin', color='CCCCCC'),
    )
    TOTAL_FONT = Font(bold=True, size=10)

    def _hdr(ws, cols):
        for c, txt in enumerate(cols, 1):
            cell = ws.cell(row=1, column=c, value=txt)
            cell.font = HDR_FONT
            cell.fill = HDR_FILL
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = BORDER
        ws.row_dimensions[1].height = 28

    def _auto_width(ws):
        for col in ws.columns:
            w = max((len(str(c.value or '')) for c in col), default=8)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(w + 4, 40)

    wb = openpyxl.Workbook()

    # ── Aba Lista ─────────────────────────────────────────────────────────────
    ws = wb.active
    ws.title = 'Comissões'
    headers = ['Nº', 'Reserva', 'Unidade', 'Cliente', 'Corretor', 'Imobiliária',
               'Beneficiário', 'Tipo Comissão', 'Valor Contrato', '% Comissão',
               'Valor Comissão', 'A Pagar']
    _hdr(ws, headers)

    qs = list(Comissao.objects.all())
    for i, c in enumerate(sorted(qs, key=lambda x: (x.unidade, x.beneficiario.lower())), 2):
        row = [
            c.numero, c.reserva, c.unidade, c.cliente, c.corretor, c.imobiliaria,
            c.beneficiario, c.tipo_comissao,
            c.valor_contrato, c.pct_comissao, c.valor_comissao, c.valor_comissao_pagar,
        ]
        for col, val in enumerate(row, 1):
            cell = ws.cell(row=i, column=col, value=val)
            cell.border = BORDER
            if col in (9, 11, 12):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
            elif col == 10:
                cell.number_format = '0.00"%"'
                cell.alignment = Alignment(horizontal='right')

    tr = len(qs) + 2
    ws.cell(row=tr, column=1, value='TOTAL').font = TOTAL_FONT
    for col, attr in [(9, 'valor_contrato'), (11, 'valor_comissao'), (12, 'valor_comissao_pagar')]:
        c = ws.cell(row=tr, column=col, value=sum(getattr(x, attr) for x in qs))
        c.number_format = '#,##0.00'
        c.font = TOTAL_FONT
    _auto_width(ws)

    # ── Aba Por Imobiliária ───────────────────────────────────────────────────
    ws2 = wb.create_sheet('Por Imobiliária')
    _hdr(ws2, ['Imobiliária', 'Vendas', 'Comissão', 'A Pagar'])
    imob_map      = defaultdict(lambda: {'comissao': 0.0, 'pagar': 0.0})
    imob_reservas = defaultdict(set)
    for c in qs:
        k = c.imobiliaria or '(sem imobiliária)'
        imob_map[k]['comissao'] += c.valor_comissao
        imob_map[k]['pagar']    += c.valor_comissao_pagar
        imob_reservas[k].add(c.reserva)
    for i, (k, v) in enumerate(sorted(imob_map.items(), key=lambda x: x[0].lower()), 2):
        for col, val in enumerate([k, len(imob_reservas[k]), v['comissao'], v['pagar']], 1):
            cell = ws2.cell(row=i, column=col, value=val)
            cell.border = BORDER
            if col in (3, 4):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
    _auto_width(ws2)

    # ── Aba Por Beneficiário ──────────────────────────────────────────────────
    ws3 = wb.create_sheet('Por Beneficiário')
    _hdr(ws3, ['Beneficiário', 'Qtde', 'Comissão', 'A Pagar'])
    benef_map = defaultdict(lambda: {'n': 0, 'comissao': 0.0, 'pagar': 0.0})
    for c in qs:
        k = c.beneficiario or '(sem beneficiário)'
        benef_map[k]['n']        += 1
        benef_map[k]['comissao'] += c.valor_comissao
        benef_map[k]['pagar']    += c.valor_comissao_pagar
    for i, (k, v) in enumerate(sorted(benef_map.items(), key=lambda x: x[0].lower()), 2):
        for col, val in enumerate([k, v['n'], v['comissao'], v['pagar']], 1):
            cell = ws3.cell(row=i, column=col, value=val)
            cell.border = BORDER
            if col in (3, 4):
                cell.number_format = '#,##0.00'
                cell.alignment = Alignment(horizontal='right')
    _auto_width(ws3)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    resp['Content-Disposition'] = 'attachment; filename="comissoes_cota365.xlsx"'
    return resp


def export_comissoes_pdf(request):
    from reportlab.platypus import HRFlowable

    qs = list(Comissao.objects.all())
    if not qs:
        return HttpResponse('Sem dados.', status=404)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=1.5*cm, rightMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
    W = doc.width
    styles = getSampleStyleSheet()

    NAVY   = colors.HexColor('#1a1a2e')
    BORDER = colors.HexColor('#dee2e6')

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    title_s = ps('T', fontSize=14, fontName='Helvetica-Bold', textColor=NAVY, spaceAfter=2)
    sub_s   = ps('S', fontSize=8,  textColor=colors.HexColor('#6c757d'), spaceAfter=8)
    sec_s   = ps('H', fontSize=10, fontName='Helvetica-Bold', textColor=NAVY,
                 spaceBefore=10, spaceAfter=4)

    def th(txt):
        return Paragraph(f'<b><font color="white">{txt}</font></b>',
                         ps('TH', fontSize=7, alignment=1))
    def td(txt):
        return Paragraph(str(txt), ps('TD', fontSize=7))
    def tdr(txt):
        return Paragraph(str(txt), ps('TR', fontSize=7, alignment=2))
    def tdb(txt):
        return Paragraph(f'<b>{txt}</b>', ps('TB', fontSize=7, alignment=2))

    def tbl(data, col_widths, total_last=False):
        t = Table(data, colWidths=col_widths, repeatRows=1)
        cmds = [
            ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
            ('GRID',          (0, 0), (-1, -1), 0.3, BORDER),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]
        if total_last:
            cmds += [
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8f0fe')),
                ('FONTNAME',   (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]
        t.setStyle(TableStyle(cmds))
        return t

    # KPIs
    reservas_vt = {}
    for c in qs:
        if c.reserva not in reservas_vt:
            reservas_vt[c.reserva] = c.valor_contrato
    total_vendas   = len(reservas_vt)
    total_contrato = sum(reservas_vt.values())
    total_comissao = sum(c.valor_comissao       for c in qs)
    total_pagar    = sum(c.valor_comissao_pagar for c in qs)

    story = []
    story.append(Paragraph('Cota 365 — Comissões', title_s))
    story.append(Paragraph(
        f'Gerado em {datetime.now().strftime("%d/%m/%Y %H:%M")}  |  {total_vendas} vendas  |  {len(qs)} linhas',
        sub_s))
    story.append(HRFlowable(width='100%', thickness=1, color=BORDER, spaceAfter=8))

    # Resumo KPI
    story.append(Paragraph('Resumo Geral', sec_s))
    story.append(tbl([
        [th('VENDAS'), th('LINHAS'), th('VALOR CONTRATOS'), th('TOTAL COMISSÕES'), th('A PAGAR')],
        [tdr(str(total_vendas)), tdr(str(len(qs))), tdr(_fmt_brl(total_contrato)),
         tdr(_fmt_brl(total_comissao)), tdr(_fmt_brl(total_pagar))],
    ], [W/5]*5))
    story.append(Spacer(1, 8))

    # Por Imobiliária
    imob_map      = defaultdict(lambda: {'comissao': 0.0, 'pagar': 0.0})
    imob_reservas = defaultdict(set)
    for c in qs:
        k = c.imobiliaria or '(sem imobiliária)'
        imob_map[k]['comissao'] += c.valor_comissao
        imob_map[k]['pagar']    += c.valor_comissao_pagar
        imob_reservas[k].add(c.reserva)

    story.append(Paragraph('Por Imobiliária', sec_s))
    imob_rows = [[th('IMOBILIÁRIA'), th('VENDAS'), th('COMISSÃO'), th('A PAGAR')]]
    for k, v in sorted(imob_map.items(), key=lambda x: x[0].lower()):
        imob_rows.append([td(k), tdr(str(len(imob_reservas[k]))),
                          tdr(_fmt_brl(v['comissao'])), tdr(_fmt_brl(v['pagar']))])
    imob_rows.append([tdb('TOTAL'), tdb(str(total_vendas)),
                      tdb(_fmt_brl(total_comissao)), tdb(_fmt_brl(total_pagar))])
    story.append(tbl(imob_rows, [W*0.48, W*0.12, W*0.20, W*0.20], total_last=True))
    story.append(Spacer(1, 8))

    # Por Beneficiário
    benef_map = defaultdict(lambda: {'n': 0, 'comissao': 0.0, 'pagar': 0.0})
    for c in qs:
        k = c.beneficiario or '(sem beneficiário)'
        benef_map[k]['n']        += 1
        benef_map[k]['comissao'] += c.valor_comissao
        benef_map[k]['pagar']    += c.valor_comissao_pagar

    story.append(Paragraph('Por Beneficiário', sec_s))
    benef_rows = [[th('BENEFICIÁRIO'), th('QTDE'), th('COMISSÃO'), th('A PAGAR')]]
    for k, v in sorted(benef_map.items(), key=lambda x: x[0].lower()):
        benef_rows.append([td(k), tdr(str(v['n'])),
                           tdr(_fmt_brl(v['comissao'])), tdr(_fmt_brl(v['pagar']))])
    benef_rows.append([tdb('TOTAL'), tdb(str(len(qs))),
                       tdb(_fmt_brl(total_comissao)), tdb(_fmt_brl(total_pagar))])
    story.append(tbl(benef_rows, [W*0.48, W*0.12, W*0.20, W*0.20], total_last=True))

    # Lista completa
    story.append(PageBreak())
    story.append(Paragraph('Lista de Comissões', sec_s))
    list_rows = [[th('Nº'), th('RESERVA'), th('UNID.'), th('CLIENTE'),
                  th('IMOBILIÁRIA'), th('BENEFICIÁRIO'), th('TIPO'), th('%'), th('COMISSÃO'), th('A PAGAR')]]
    for c in sorted(qs, key=lambda x: (x.unidade, x.beneficiario.lower())):
        list_rows.append([
            td(c.numero), td(c.reserva), td(c.unidade),
            td(c.cliente[:22] if c.cliente else ''),
            td(c.imobiliaria[:20] if c.imobiliaria else ''),
            td(c.beneficiario[:20] if c.beneficiario else ''),
            td(c.tipo_comissao[:10]),
            tdr(f"{c.pct_comissao:.1f}%".replace('.', ',')),
            tdr(_fmt_brl(c.valor_comissao)),
            tdr(_fmt_brl(c.valor_comissao_pagar)),
        ])
    list_rows.append([tdb('TOTAL'), tdb(''), tdb(''), tdb(''), tdb(''), tdb(''), tdb(''), tdb(''),
                      tdb(_fmt_brl(total_comissao)), tdb(_fmt_brl(total_pagar))])
    story.append(tbl(list_rows,
                     [W*0.04, W*0.06, W*0.06, W*0.14, W*0.14, W*0.14, W*0.08, W*0.06, W*0.14, W*0.14],
                     total_last=True))

    doc.build(story)
    buf.seek(0)
    resp = HttpResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'attachment; filename="comissoes_cota365.pdf"'
    return resp
