import io
from datetime import datetime

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import FileResponse, HttpResponse
from django.shortcuts import render

from .models import ImportacaoFaturamento, Recebimento


_MESES_PT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']


def _fmt_mes(d):
    return f'{_MESES_PT[d.month - 1]}/{d.year}'


def _fmt_brl(v):
    v = v or 0
    return 'R$\xa0' + f'{float(v):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _aplicar_filtros(qs, filtros):
    if filtros['empresa']:
        qs = qs.filter(codigo_empresa=filtros['empresa'])
    if filtros['empreendimento']:
        qs = qs.filter(codigo_centro_custo=filtros['empreendimento'])
    if filtros['data_inicio']:
        qs = qs.filter(data_baixa__gte=filtros['data_inicio'])
    if filtros['data_fim']:
        qs = qs.filter(data_baixa__lte=filtros['data_fim'])
    return qs


def _resolve_filtros(request, importacao):
    """Lê os filtros da querystring e monta o queryset base + opções dos selects."""
    filtros = {
        'empresa': request.GET.get('empresa', ''),
        'empreendimento': request.GET.get('empreendimento', ''),
        'data_inicio': request.GET.get('data_inicio', ''),
        'data_fim': request.GET.get('data_fim', ''),
    }

    base_qs = Recebimento.objects.filter(importacao=importacao)

    # opções de empreendimento respeitam a empresa já escolhida, para não
    # listar empreendimentos de outra empresa no filtro
    qs_para_empreendimentos = base_qs
    if filtros['empresa']:
        qs_para_empreendimentos = qs_para_empreendimentos.filter(codigo_empresa=filtros['empresa'])

    opcoes = {
        'empresas': list(
            base_qs.values('codigo_empresa', 'nome_empresa').distinct().order_by('nome_empresa')
        ),
        'empreendimentos': list(
            qs_para_empreendimentos.values('codigo_centro_custo', 'nome_centro_custo')
                                    .distinct().order_by('nome_centro_custo')
        ),
    }

    qs = _aplicar_filtros(base_qs, filtros)
    return qs, filtros, opcoes


def _build_resumo(qs):
    por_categoria = {c: 0 for c, _ in Recebimento.CATEGORIA_CHOICES}
    for row in qs.values('categoria').annotate(total=Sum('valor_liquido')):
        por_categoria[row['categoria']] = row['total']
    total_geral = sum(por_categoria.values())

    fluxo_por_mes = {}
    for row in (
        qs.annotate(mes=TruncMonth('data_baixa'))
          .values('mes', 'categoria')
          .annotate(total=Sum('valor_liquido'))
          .order_by('mes')
    ):
        mes = row['mes']
        fluxo_por_mes.setdefault(mes, {c: 0 for c, _ in Recebimento.CATEGORIA_CHOICES})
        fluxo_por_mes[mes][row['categoria']] = row['total']

    fluxo_mensal = []
    for mes, valores in sorted(fluxo_por_mes.items()):
        incorporacao = valores[Recebimento.INCORPORACAO]
        locacao = valores[Recebimento.LOCACAO]
        outros = valores[Recebimento.OUTROS]
        fluxo_mensal.append({
            'mes': mes,
            'mes_label': _fmt_mes(mes),
            'incorporacao': incorporacao,
            'locacao': locacao,
            'outros': outros,
            'total': incorporacao + locacao + outros,
        })

    por_empresa = list(
        qs.values('nome_empresa')
          .annotate(total=Sum('valor_liquido'))
          .order_by('-total')
    )

    por_empreendimento_raw = list(
        qs.values('nome_centro_custo', 'categoria')
          .annotate(total=Sum('valor_liquido'))
          .order_by('-total')
    )
    por_empreendimento = {
        Recebimento.INCORPORACAO: [r for r in por_empreendimento_raw if r['categoria'] == Recebimento.INCORPORACAO],
        Recebimento.LOCACAO: [r for r in por_empreendimento_raw if r['categoria'] == Recebimento.LOCACAO],
        Recebimento.OUTROS: [r for r in por_empreendimento_raw if r['categoria'] == Recebimento.OUTROS],
    }

    return {
        'total_incorporacao': por_categoria[Recebimento.INCORPORACAO],
        'total_locacao': por_categoria[Recebimento.LOCACAO],
        'total_outros': por_categoria[Recebimento.OUTROS],
        'total_geral': total_geral,
        'fluxo_mensal': fluxo_mensal,
        'por_empresa': por_empresa,
        'por_empreendimento_incorporacao': por_empreendimento[Recebimento.INCORPORACAO],
        'por_empreendimento_locacao': por_empreendimento[Recebimento.LOCACAO],
        'por_empreendimento_outros': por_empreendimento[Recebimento.OUTROS],
    }


def resumo(request):
    importacao = ImportacaoFaturamento.objects.first()
    contexto = {'importacao': importacao, 'resumo': None, 'filtros': {}, 'opcoes': {}}
    if not importacao:
        return render(request, 'faturamento/resumo.html', contexto)

    qs, filtros, opcoes = _resolve_filtros(request, importacao)

    contexto['resumo'] = _build_resumo(qs)
    contexto['filtros'] = filtros
    contexto['opcoes'] = opcoes
    return render(request, 'faturamento/resumo.html', contexto)


# ── PDF ───────────────────────────────────────────────────────────────────────

def _descricao_filtros(qs, filtros):
    partes = []
    if filtros['empresa']:
        nome = qs.values_list('nome_empresa', flat=True).first() or filtros['empresa']
        partes.append(f'Empresa: {nome}')
    if filtros['empreendimento']:
        nome = qs.values_list('nome_centro_custo', flat=True).first() or filtros['empreendimento']
        partes.append(f'Empreendimento: {nome}')
    if filtros['data_inicio'] or filtros['data_fim']:
        ini = filtros['data_inicio'] or '—'
        fim = filtros['data_fim'] or '—'
        partes.append(f'Período: {ini} a {fim}')
    return '  |  '.join(partes)


def exportar_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    importacao = ImportacaoFaturamento.objects.first()
    if not importacao:
        return HttpResponse('Nenhum dado importado.', status=404)

    qs, filtros, _ = _resolve_filtros(request, importacao)
    resumo_ctx = _build_resumo(qs)
    descricao_filtros = _descricao_filtros(qs, filtros)

    C_NAVY = colors.HexColor('#1a1a2e')
    C_GREEN = colors.HexColor('#198754')
    C_LIGHT = colors.HexColor('#f4f7fb')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.6*cm, rightMargin=1.6*cm,
        topMargin=1.2*cm, bottomMargin=1.4*cm,
    )
    W = doc.width
    styles = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    title_s = ps('fptitle', fontSize=15, leading=18, fontName='Helvetica-Bold', textColor=C_NAVY)
    sub_s = ps('fpsub', fontSize=8.5, leading=12, textColor=colors.HexColor('#6c757d'))
    filtro_s = ps('fpfiltro', fontSize=8, leading=11, textColor=colors.HexColor('#495057'))
    hdr_s = ps('fph', fontSize=7.5, leading=10, alignment=1, fontName='Helvetica-Bold', textColor=colors.white)
    cell_s = ps('fpc', fontSize=8, leading=11)
    cell_r = ps('fpcr', fontSize=8, leading=11, alignment=2)
    tot_s = ps('fptot', fontSize=8, leading=11, fontName='Helvetica-Bold')
    tot_r = ps('fptotr', fontSize=8, leading=11, alignment=2, fontName='Helvetica-Bold')

    story = [
        Paragraph('RESUMO DE FATURAMENTO', title_s),
        Paragraph('Recebimentos consolidados por Incorporação e Locações — valores líquidos (Sienge)', sub_s),
        Spacer(1, 0.15*cm),
        Paragraph(
            f'Última importação: {importacao.arquivo} em {importacao.importado_em:%d/%m/%Y %H:%M} '
            f'({importacao.total_linhas} linhas)  |  Gerado em {datetime.now():%d/%m/%Y %H:%M}',
            filtro_s,
        ),
    ]
    if descricao_filtros:
        story.append(Paragraph(f'Filtros aplicados: {descricao_filtros}', filtro_s))
    story.append(Spacer(1, 0.5*cm))

    # ── Cards de totais ──────────────────────────────────────────────────────
    cards_data = [[
        Paragraph('<font color="#6c757d" size="7.5"><b>INCORPORAÇÃO</b></font>', cell_s),
        Paragraph('<font color="#6c757d" size="7.5"><b>LOCAÇÕES</b></font>', cell_s),
        Paragraph('<font color="#6c757d" size="7.5"><b>TOTAL GERAL</b></font>', cell_s),
    ], [
        Paragraph(f'<b><font size="13">{_fmt_brl(resumo_ctx["total_incorporacao"])}</font></b>', cell_s),
        Paragraph(f'<b><font size="13">{_fmt_brl(resumo_ctx["total_locacao"])}</font></b>', cell_s),
        Paragraph(f'<b><font size="13">{_fmt_brl(resumo_ctx["total_geral"])}</font></b>', cell_s),
    ]]
    cards_tbl = Table(cards_data, colWidths=[W/3]*3)
    cards_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), C_LIGHT),
        ('BOX', (0, 0), (0, -1), 1, colors.HexColor('#0d6efd')),
        ('BOX', (1, 0), (1, -1), 1, C_GREEN),
        ('BOX', (2, 0), (2, -1), 1, C_NAVY),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
    ]))
    story.append(cards_tbl)
    story.append(Spacer(1, 0.6*cm))

    def tabela_titulo(txt):
        return Paragraph(f'<b><font size="10" color="#1a1a2e">{txt}</font></b>', ps('sect', spaceAfter=4))

    # ── Fluxo Mensal ─────────────────────────────────────────────────────────
    story.append(tabela_titulo('FLUXO MENSAL'))
    fluxo_header = [Paragraph('MÊS', hdr_s), Paragraph('INCORPORAÇÃO', hdr_s),
                     Paragraph('LOCAÇÕES', hdr_s), Paragraph('TOTAL', hdr_s)]
    fluxo_rows = [fluxo_header]
    for linha in resumo_ctx['fluxo_mensal']:
        fluxo_rows.append([
            Paragraph(linha['mes_label'], cell_s),
            Paragraph(_fmt_brl(linha['incorporacao']), cell_r),
            Paragraph(_fmt_brl(linha['locacao']), cell_r),
            Paragraph(f'<b>{_fmt_brl(linha["total"])}</b>', cell_r),
        ])
    fluxo_rows.append([
        Paragraph('TOTAL', tot_s),
        Paragraph(_fmt_brl(resumo_ctx['total_incorporacao']), tot_r),
        Paragraph(_fmt_brl(resumo_ctx['total_locacao']), tot_r),
        Paragraph(_fmt_brl(resumo_ctx['total_geral']), tot_r),
    ])
    fluxo_tbl = Table(fluxo_rows, colWidths=[W*0.22, W*0.26, W*0.26, W*0.26], repeatRows=1)
    fluxo_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), C_NAVY),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, -1), (-1, -1), C_LIGHT),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#adb5bd')),
    ]
    for i in range(1, len(fluxo_rows) - 1):
        if i % 2 == 0:
            fluxo_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafbfc')))
    fluxo_tbl.setStyle(TableStyle(fluxo_cmds))
    story.append(fluxo_tbl)
    story.append(Spacer(1, 0.6*cm))

    def tabela_agrupada(titulo, linhas, campo_label, subtotal=None):
        elementos = [tabela_titulo(titulo)]
        header = [Paragraph(campo_label, hdr_s), Paragraph('TOTAL RECEBIDO', hdr_s)]
        rows = [header]
        for linha in linhas:
            rows.append([
                Paragraph(linha.get('nome_empresa') or linha.get('nome_centro_custo') or '', cell_s),
                Paragraph(_fmt_brl(linha['total']), cell_r),
            ])
        if subtotal is not None:
            rows.append([
                Paragraph('<b>Subtotal</b>', tot_s),
                Paragraph(_fmt_brl(subtotal), tot_r),
            ])
        tbl = Table(rows, colWidths=[W*0.65, W*0.35], repeatRows=1)
        cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), C_NAVY),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(rows)):
            if i % 2 == 0:
                cmds.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafbfc')))
        if subtotal is not None:
            cmds.append(('BACKGROUND', (0, -1), (-1, -1), C_LIGHT))
            cmds.append(('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#adb5bd')))
        tbl.setStyle(TableStyle(cmds))
        elementos.append(tbl)
        return [KeepTogether(elementos)]

    story += tabela_agrupada('POR EMPRESA', resumo_ctx['por_empresa'], 'EMPRESA')
    story.append(Spacer(1, 0.6*cm))
    story += tabela_agrupada('POR EMPREENDIMENTO — INCORPORAÇÃO',
                              resumo_ctx['por_empreendimento_incorporacao'], 'EMPREENDIMENTO',
                              subtotal=resumo_ctx['total_incorporacao'])
    story.append(Spacer(1, 0.6*cm))
    story += tabela_agrupada('POR EMPREENDIMENTO — LOCAÇÕES',
                              resumo_ctx['por_empreendimento_locacao'], 'EMPREENDIMENTO',
                              subtotal=resumo_ctx['total_locacao'])
    if resumo_ctx['por_empreendimento_outros']:
        story.append(Spacer(1, 0.6*cm))
        story += tabela_agrupada('POR EMPREENDIMENTO — OUTROS',
                                  resumo_ctx['por_empreendimento_outros'], 'EMPREENDIMENTO',
                                  subtotal=resumo_ctx['total_outros'])

    doc.build(story)
    buf.seek(0)
    resp = FileResponse(buf, content_type='application/pdf')
    resp['Content-Disposition'] = 'inline; filename="Faturamento_Resumo.pdf"'
    return resp
