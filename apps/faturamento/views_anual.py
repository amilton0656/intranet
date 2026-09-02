"""Análise anual em 3 estágios: resumo por empresa -> fluxo mensal da
empresa -> detalhe do mês. Usa Recebimento (dinheiro que entrou) para
Incorporação/Locação/Recebimentos e Contrato (valor total vendido) para
Vendas."""

import io
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import FileResponse, Http404
from django.shortcuts import render

from .models import Contrato, Recebimento
from .views import _fmt_brl, _fmt_mes


def _empresas_disponiveis():
    empresas = {}
    for codigo, nome in Recebimento.objects.values_list('codigo_empresa', 'nome_empresa').distinct():
        if codigo:
            empresas[codigo] = nome
    for codigo, nome in Contrato.objects.values_list('codigo_empresa', 'nome_empresa').distinct():
        if codigo:
            empresas.setdefault(codigo, nome)
    return sorted(empresas.items(), key=lambda x: x[1])


def _proximo_mes(d):
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _mes_menos(d, n):
    """Primeiro dia do mês, `n` meses antes de `d`."""
    total = d.year * 12 + (d.month - 1) - n
    return date(total // 12, total % 12 + 1, 1)


def _parse_mes(s):
    """Converte 'YYYY-MM' (input type=month) em date do primeiro dia do mês."""
    s = (s or '').strip()
    if not s:
        return None
    try:
        ano, mes = s.split('-')
        return date(int(ano), int(mes), 1)
    except (ValueError, AttributeError):
        return None


def _build_resumo_anual(request):
    """Monta o contexto do pivô (estágio 1) — reaproveitado pela tela e pelo PDF.

    Sem filtro, mostra os últimos 12 meses (janela rolante a partir de hoje).
    Com filtro de período, um dos dois lados pode ficar em aberto: só início
    vai até o mês atual, só fim mostra os 12 meses terminando nele.
    """
    empresas = _empresas_disponiveis()
    codigos = [codigo for codigo, _ in empresas]

    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)

    filtro_inicio = _parse_mes(request.GET.get('data_inicio', ''))
    filtro_fim = _parse_mes(request.GET.get('data_fim', ''))

    if filtro_inicio or filtro_fim:
        fim = filtro_fim or mes_atual
        inicio = filtro_inicio or _mes_menos(fim, 11)
        if inicio > fim:
            inicio, fim = fim, inicio
        meses = []
        m = inicio
        while m <= fim:
            meses.append(m)
            m = _proximo_mes(m)
    else:
        meses = [_mes_menos(mes_atual, i) for i in range(11, -1, -1)]

    filtros = {
        'data_inicio': request.GET.get('data_inicio', ''),
        'data_fim': request.GET.get('data_fim', ''),
    }

    recebido = defaultdict(lambda: Decimal('0'))
    for row in (Recebimento.objects.filter(codigo_empresa__in=codigos)
                .annotate(mes=TruncMonth('data_baixa'))
                .values('codigo_empresa', 'mes')
                .annotate(total=Sum('valor_liquido'))):
        recebido[(row['codigo_empresa'], row['mes'])] = row['total']

    # mes_venda_efetivo é uma property Python — soma em Python (poucas
    # centenas de contratos no total, tranquilo).
    vendas = defaultdict(lambda: Decimal('0'))
    for c in Contrato.objects.filter(codigo_empresa__in=codigos, categoria=Recebimento.INCORPORACAO):
        efetivo = c.mes_venda_efetivo
        if efetivo:
            vendas[(c.codigo_empresa, date(efetivo.year, efetivo.month, 1))] += c.valor_total

    linhas = []
    totais_col = [{'vendas': Decimal('0'), 'recebimentos': Decimal('0')} for _ in empresas]
    total_geral_vendas = Decimal('0')
    total_geral_recebimentos = Decimal('0')

    for mes in meses:
        colunas = []
        linha_vendas = Decimal('0')
        linha_recebimentos = Decimal('0')
        for i, (codigo, nome) in enumerate(empresas):
            v = vendas.get((codigo, mes), Decimal('0'))
            r = recebido.get((codigo, mes), Decimal('0'))
            colunas.append({'codigo_empresa': codigo, 'nome_empresa': nome, 'vendas': v, 'recebimentos': r})
            totais_col[i]['vendas'] += v
            totais_col[i]['recebimentos'] += r
            linha_vendas += v
            linha_recebimentos += r
        total_geral_vendas += linha_vendas
        total_geral_recebimentos += linha_recebimentos
        linhas.append({
            'mes': mes,
            'mes_label': _fmt_mes(mes),
            'colunas': colunas,
            'total_vendas': linha_vendas,
            'total_recebimentos': linha_recebimentos,
        })

    rodape = [
        {'codigo_empresa': codigo, 'nome_empresa': nome,
         'vendas': totais_col[i]['vendas'], 'recebimentos': totais_col[i]['recebimentos']}
        for i, (codigo, nome) in enumerate(empresas)
    ]

    return {
        'empresas': empresas,
        'linhas': linhas,
        'rodape': rodape,
        'total_geral_vendas': total_geral_vendas,
        'total_geral_recebimentos': total_geral_recebimentos,
        'filtros': filtros,
    }


def resumo(request):
    contexto = _build_resumo_anual(request)
    return render(request, 'faturamento/anual_resumo.html', contexto)


def fluxo_empresa(request, codigo_empresa):
    """Estágio 2 — fluxo mensal de uma empresa: Vendas | Incorporação | Locações | Total."""
    recebimentos = Recebimento.objects.filter(codigo_empresa=codigo_empresa)
    contratos = Contrato.objects.filter(codigo_empresa=codigo_empresa, categoria=Recebimento.INCORPORACAO)

    nome_empresa = recebimentos.values_list('nome_empresa', flat=True).first()
    if not nome_empresa:
        nome_empresa = (Contrato.objects.filter(codigo_empresa=codigo_empresa)
                         .values_list('nome_empresa', flat=True).first())
    if not nome_empresa:
        raise Http404('Empresa não encontrada.')

    meses = defaultdict(lambda: {'vendas': 0, 'incorporacao': 0, 'locacao': 0})

    for row in (recebimentos.annotate(mes=TruncMonth('data_baixa'))
                .values('mes', 'categoria')
                .annotate(total=Sum('valor_liquido'))):
        if row['categoria'] == Recebimento.INCORPORACAO:
            meses[row['mes']]['incorporacao'] += row['total']
        elif row['categoria'] == Recebimento.LOCACAO:
            meses[row['mes']]['locacao'] += row['total']

    # mes_venda_efetivo é uma property Python (mes_venda_manual ou
    # mes_venda) — poucos contratos por empresa, soma direto em Python.
    for c in contratos:
        efetivo = c.mes_venda_efetivo
        if efetivo:
            meses[date(efetivo.year, efetivo.month, 1)]['vendas'] += c.valor_total

    linhas = []
    for mes in sorted(meses):
        v = meses[mes]
        linhas.append({
            'mes': mes,
            'mes_label': _fmt_mes(mes),
            'vendas': v['vendas'],
            'incorporacao': v['incorporacao'],
            'locacao': v['locacao'],
            'total': v['incorporacao'] + v['locacao'],
        })

    totais = {
        'vendas': sum(l['vendas'] for l in linhas),
        'incorporacao': sum(l['incorporacao'] for l in linhas),
        'locacao': sum(l['locacao'] for l in linhas),
        'total': sum(l['total'] for l in linhas),
    }

    return render(request, 'faturamento/anual_fluxo_empresa.html', {
        'codigo_empresa': codigo_empresa,
        'nome_empresa': nome_empresa,
        'linhas': linhas,
        'totais': totais,
    })


def _detalhe_mes(inicio, fim, codigo_empresa=None):
    """Monta vendas/incorporação/locação de um mês, opcionalmente restrito a
    uma empresa. `codigo_empresa=None` = todas as empresas (visão consolidada)."""
    recebimentos_qs = Recebimento.objects.filter(data_baixa__gte=inicio, data_baixa__lt=fim)
    contratos_qs = Contrato.objects.filter(categoria=Recebimento.INCORPORACAO)
    if codigo_empresa:
        recebimentos_qs = recebimentos_qs.filter(codigo_empresa=codigo_empresa)
        contratos_qs = contratos_qs.filter(codigo_empresa=codigo_empresa)

    recebimentos = list(recebimentos_qs.order_by('nome_centro_custo', 'nome_cliente'))
    incorporacao = [r for r in recebimentos if r.categoria == Recebimento.INCORPORACAO]
    locacao = [r for r in recebimentos if r.categoria == Recebimento.LOCACAO]

    vendas = sorted(
        (c for c in contratos_qs if c.mes_venda_efetivo and inicio <= c.mes_venda_efetivo < fim),
        key=lambda c: c.nome_cliente,
    )

    return {
        'vendas': vendas,
        'incorporacao': incorporacao,
        'locacao': locacao,
        'total_vendas': sum(c.valor_total for c in vendas),
        'total_incorporacao': sum(r.valor_liquido for r in incorporacao),
        'total_locacao': sum(r.valor_liquido for r in locacao),
    }


def detalhe_mes(request, codigo_empresa, ano, mes):
    """Estágio 3 — o que constitui o valor daquele mês numa empresa (vendas, incorporação, locação)."""
    try:
        inicio = date(ano, mes, 1)
    except ValueError:
        raise Http404('Mês inválido.')
    fim = _proximo_mes(inicio)

    contexto = _detalhe_mes(inicio, fim, codigo_empresa)

    nome_empresa = (
        contexto['incorporacao'][0].nome_empresa if contexto['incorporacao']
        else (contexto['locacao'][0].nome_empresa if contexto['locacao']
              else (contexto['vendas'][0].nome_empresa if contexto['vendas'] else ''))
    )
    if not nome_empresa:
        nome_empresa = (Contrato.objects.filter(codigo_empresa=codigo_empresa)
                         .values_list('nome_empresa', flat=True).first()) or ''

    contexto.update({
        'codigo_empresa': codigo_empresa,
        'nome_empresa': nome_empresa,
        'mes': inicio,
        'mes_label': _fmt_mes(inicio),
    })
    return render(request, 'faturamento/anual_detalhe_mes.html', contexto)


def detalhe_mes_geral(request, ano, mes):
    """Estágio 1 -> detalhe — o que constitui o valor daquele mês, todas as empresas juntas."""
    try:
        inicio = date(ano, mes, 1)
    except ValueError:
        raise Http404('Mês inválido.')
    fim = _proximo_mes(inicio)

    contexto = _detalhe_mes(inicio, fim)
    contexto.update({
        'codigo_empresa': None,
        'nome_empresa': None,
        'mes': inicio,
        'mes_label': _fmt_mes(inicio),
    })
    return render(request, 'faturamento/anual_detalhe_mes.html', contexto)


# ── PDF ───────────────────────────────────────────────────────────────────────

def exportar_pdf(request):
    """PDF do pivô (estágio 1) — mesma tabela da tela, paisagem por causa da largura."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    contexto = _build_resumo_anual(request)
    if not contexto['linhas']:
        return FileResponse(io.BytesIO(b''), content_type='application/pdf', filename='vazio.pdf')

    C_NAVY = colors.HexColor('#1a1a2e')
    C_GOLD = colors.HexColor('#c8a951')
    C_LIGHT = colors.HexColor('#f4f7fb')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=1.2*cm, rightMargin=1.2*cm,
        topMargin=1.1*cm, bottomMargin=1.2*cm,
    )
    W = doc.width
    styles = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    title_s = ps('atitle', fontSize=14, leading=17, fontName='Helvetica-Bold', textColor=C_NAVY)
    sub_s = ps('asub', fontSize=8, leading=11, textColor=colors.HexColor('#6c757d'))
    hdr1_s = ps('ah1', fontSize=8, leading=10, alignment=1, fontName='Helvetica-Bold', textColor=colors.white)
    hdr2_s = ps('ah2', fontSize=7, leading=9, alignment=1, fontName='Helvetica-Bold', textColor=colors.white)
    hdr2_gold_s = ps('ah2g', fontSize=7, leading=9, alignment=1, fontName='Helvetica-Bold', textColor=C_GOLD)
    cell_s = ps('acell', fontSize=7.5, leading=10)
    cell_r = ps('acellr', fontSize=7.5, leading=10, alignment=2)
    tot_s = ps('atot', fontSize=7.5, leading=10, fontName='Helvetica-Bold')
    tot_r = ps('atotr', fontSize=7.5, leading=10, alignment=2, fontName='Helvetica-Bold')

    periodo_desc = f'{contexto["linhas"][0]["mes_label"]} a {contexto["linhas"][-1]["mes_label"]}'

    story = [
        Paragraph('FATURAMENTOS POR PERÍODO — GRUPO COTA', title_s),
        Paragraph('Vendas (valor total contratado) x Faturamento (dinheiro que entrou), por empresa', sub_s),
        Spacer(1, 0.1*cm),
        Paragraph(f'Período: {periodo_desc}  |  Gerado em {datetime.now():%d/%m/%Y %H:%M}', sub_s),
        Spacer(1, 0.4*cm),
    ]

    empresas = contexto['empresas']
    n_emp = len(empresas)

    header1 = [Paragraph('MÊS', hdr1_s)]
    for _, nome in empresas:
        header1.append(Paragraph(nome.upper(), hdr1_s))
        header1.append('')
    header1.append(Paragraph('TOTAL GERAL', hdr1_s))
    header1.append('')

    header2 = ['']
    for _ in empresas:
        header2.append(Paragraph('VENDAS', hdr2_gold_s))
        header2.append(Paragraph('FATURAMENTO', hdr2_s))
    header2.append(Paragraph('VENDAS', hdr2_gold_s))
    header2.append(Paragraph('FATURAMENTO', hdr2_s))

    rows = [header1, header2]
    for linha in contexto['linhas']:
        row = [Paragraph(linha['mes_label'], cell_s)]
        for coluna in linha['colunas']:
            row.append(Paragraph(_fmt_brl(coluna['vendas']), cell_r))
            row.append(Paragraph(_fmt_brl(coluna['recebimentos']), cell_r))
        row.append(Paragraph(f'<b>{_fmt_brl(linha["total_vendas"])}</b>', cell_r))
        row.append(Paragraph(f'<b>{_fmt_brl(linha["total_recebimentos"])}</b>', cell_r))
        rows.append(row)

    total_row = [Paragraph('TOTAL', tot_s)]
    for col in contexto['rodape']:
        total_row.append(Paragraph(_fmt_brl(col['vendas']), tot_r))
        total_row.append(Paragraph(_fmt_brl(col['recebimentos']), tot_r))
    total_row.append(Paragraph(_fmt_brl(contexto['total_geral_vendas']), tot_r))
    total_row.append(Paragraph(_fmt_brl(contexto['total_geral_recebimentos']), tot_r))
    rows.append(total_row)

    n_cols = 1 + (n_emp + 1) * 2
    mes_w = W * 0.08
    resto_w = (W - mes_w) / (n_cols - 1)
    col_widths = [mes_w] + [resto_w] * (n_cols - 1)

    tbl = Table(rows, colWidths=col_widths, repeatRows=2)
    cmds = [
        ('BACKGROUND', (0, 0), (-1, 1), C_NAVY),
        ('SPAN', (0, 0), (0, 1)),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, -1), (-1, -1), C_LIGHT),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#adb5bd')),
    ]
    col = 1
    for _ in empresas:
        cmds.append(('SPAN', (col, 0), (col + 1, 0)))
        col += 2
    cmds.append(('SPAN', (col, 0), (col + 1, 0)))
    for i in range(2, len(rows) - 1):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafbfc')))
    tbl.setStyle(TableStyle(cmds))
    story.append(tbl)

    doc.build(story)
    buf.seek(0)
    resp = FileResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="Faturamento_Por_Periodo.pdf"'
    return resp
