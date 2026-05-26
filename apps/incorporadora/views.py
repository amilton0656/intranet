from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from .models import Empresa, Empreendimento, Bloco, Unidade
from .forms import EmpresaForm, EmpreendimentoForm, BlocoForm, UnidadeForm
from .utils import render_to_pdf


# ── Empresa ──────────────────────────────────────────────────────────────────

@login_required
def empresa_list(request):
    empresas = Empresa.objects.all()
    return render(request, 'incorporadora/empresa_list.html', {'empresas': empresas})


@login_required
def empresa_create(request):
    form = EmpresaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Empresa cadastrada com sucesso.')
        return redirect('incorporadora:empresa_list')
    return render(request, 'incorporadora/empresa_form.html', {'form': form, 'titulo': 'Nova Empresa'})


@login_required
def empresa_edit(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    form = EmpresaForm(request.POST or None, instance=empresa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Empresa atualizada com sucesso.')
        return redirect('incorporadora:empresa_list')
    return render(request, 'incorporadora/empresa_form.html', {'form': form, 'titulo': 'Editar Empresa', 'empresa': empresa})


@login_required
def empresa_delete(request, pk):
    empresa = get_object_or_404(Empresa, pk=pk)
    if request.method == 'POST':
        empresa.delete()
        messages.success(request, 'Empresa excluída com sucesso.')
        return redirect('incorporadora:empresa_list')
    return render(request, 'incorporadora/empresa_confirm_delete.html', {'empresa': empresa})


# ── Empreendimento ───────────────────────────────────────────────────────────

@login_required
def empreendimento_list(request):
    empreendimentos = Empreendimento.objects.select_related('empresa').all()
    return render(request, 'incorporadora/empreendimento_list.html', {'empreendimentos': empreendimentos})


@login_required
def empreendimento_create(request):
    form = EmpreendimentoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Empreendimento cadastrado com sucesso.')
        return redirect('incorporadora:empreendimento_list')
    return render(request, 'incorporadora/empreendimento_form.html', {'form': form, 'titulo': 'Novo Empreendimento'})


@login_required
def empreendimento_edit(request, pk):
    obj = get_object_or_404(Empreendimento, pk=pk)
    form = EmpreendimentoForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Empreendimento atualizado com sucesso.')
        return redirect('incorporadora:empreendimento_list')
    return render(request, 'incorporadora/empreendimento_form.html', {'form': form, 'titulo': 'Editar Empreendimento', 'obj': obj})


@login_required
def empreendimento_delete(request, pk):
    obj = get_object_or_404(Empreendimento, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, 'Empreendimento excluído com sucesso.')
        return redirect('incorporadora:empreendimento_list')
    return render(request, 'incorporadora/empreendimento_confirm_delete.html', {'obj': obj})


# ── Bloco ─────────────────────────────────────────────────────────────────────

@login_required
def bloco_list(request, empreendimento_pk):
    empreendimento = get_object_or_404(Empreendimento, pk=empreendimento_pk)
    blocos = empreendimento.blocos.all()
    return render(request, 'incorporadora/bloco_list.html', {'empreendimento': empreendimento, 'blocos': blocos})


@login_required
def bloco_create(request, empreendimento_pk):
    empreendimento = get_object_or_404(Empreendimento, pk=empreendimento_pk)
    form = BlocoForm(request.POST or None, initial={'empreendimento': empreendimento})
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bloco cadastrado com sucesso.')
        return redirect('incorporadora:bloco_list', empreendimento_pk=empreendimento.pk)
    return render(request, 'incorporadora/bloco_form.html', {
        'form': form, 'titulo': 'Novo Bloco', 'empreendimento': empreendimento,
    })


@login_required
def bloco_edit(request, pk):
    bloco = get_object_or_404(Bloco, pk=pk)
    form = BlocoForm(request.POST or None, instance=bloco)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Bloco atualizado com sucesso.')
        return redirect('incorporadora:bloco_list', empreendimento_pk=bloco.empreendimento.pk)
    return render(request, 'incorporadora/bloco_form.html', {
        'form': form, 'titulo': 'Editar Bloco', 'empreendimento': bloco.empreendimento, 'obj': bloco,
    })


@login_required
def bloco_delete(request, pk):
    bloco = get_object_or_404(Bloco, pk=pk)
    empreendimento_pk = bloco.empreendimento.pk
    if request.method == 'POST':
        bloco.delete()
        messages.success(request, 'Bloco excluído com sucesso.')
        return redirect('incorporadora:bloco_list', empreendimento_pk=empreendimento_pk)
    return render(request, 'incorporadora/bloco_confirm_delete.html', {'obj': bloco})


# ── Unidade ───────────────────────────────────────────────────────────────────

@login_required
def unidade_list(request, bloco_pk):
    bloco    = get_object_or_404(Bloco.objects.select_related('empreendimento'), pk=bloco_pk)
    unidades = bloco.unidades.all()

    f_numero    = request.GET.get('numero', '').strip()
    f_tipo      = request.GET.get('tipo', '').strip()
    f_tipologia = request.GET.get('tipologia', '').strip()
    f_local     = request.GET.get('localizacao', '').strip()
    f_status    = request.GET.get('status', '').strip()

    if f_numero:
        unidades = unidades.filter(numero__icontains=f_numero)
    if f_tipo:
        unidades = unidades.filter(tipo=f_tipo)
    if f_tipologia:
        unidades = unidades.filter(tipologia__icontains=f_tipologia)
    if f_local:
        unidades = unidades.filter(localizacao__icontains=f_local)
    if f_status:
        unidades = unidades.filter(status=f_status)

    filtros_ativos = any([f_numero, f_tipo, f_tipologia, f_local, f_status])

    return render(request, 'incorporadora/unidade_list.html', {
        'bloco':          bloco,
        'unidades':       unidades,
        'tipo_choices':   Unidade.TIPO_CHOICES,
        'status_choices': Unidade.STATUS_CHOICES,
        'filtros':        {'numero': f_numero, 'tipo': f_tipo, 'tipologia': f_tipologia,
                           'localizacao': f_local, 'status': f_status},
        'filtros_ativos': filtros_ativos,
    })


@login_required
def unidade_create(request, bloco_pk):
    bloco = get_object_or_404(Bloco.objects.select_related('empreendimento'), pk=bloco_pk)
    form = UnidadeForm(request.POST or None, initial={'bloco': bloco}, bloco=bloco)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Unidade cadastrada com sucesso.')
        return redirect('incorporadora:unidade_list', bloco_pk=bloco.pk)
    return render(request, 'incorporadora/unidade_form.html', {'form': form, 'titulo': 'Nova Unidade', 'bloco': bloco})


@login_required
def unidade_edit(request, pk):
    unidade = get_object_or_404(Unidade.objects.select_related('bloco__empreendimento'), pk=pk)
    form = UnidadeForm(request.POST or None, instance=unidade, bloco=unidade.bloco)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Unidade atualizada com sucesso.')
        return redirect('incorporadora:unidade_list', bloco_pk=unidade.bloco.pk)
    return render(request, 'incorporadora/unidade_form.html', {
        'form': form, 'titulo': 'Editar Unidade', 'bloco': unidade.bloco, 'obj': unidade,
    })


@login_required
def unidade_delete(request, pk):
    unidade = get_object_or_404(Unidade.objects.select_related('bloco__empreendimento'), pk=pk)
    bloco_pk = unidade.bloco.pk
    if request.method == 'POST':
        unidade.delete()
        messages.success(request, 'Unidade excluída com sucesso.')
        return redirect('incorporadora:unidade_list', bloco_pk=bloco_pk)
    return render(request, 'incorporadora/unidade_confirm_delete.html', {'obj': unidade})


# ── PDF exports ───────────────────────────────────────────────────────────────

@login_required
def empreendimento_export_excel(request):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Unidades'

    headers = [
        'Empreendimento', 'Bloco', 'Ordem', 'Número', 'Números Adicionais', 'Tipo', 'Tipologia', 'Localização',
        'Área Privativa (m²)', 'Área Priv. Acess. (m²)', 'Área Comum (m²)',
        'Fração Ideal', 'Valor Tabela (R$)', 'Status',
        'Descrição 1', 'Descrição 2', 'Descrição 3',
    ]
    hdr_font = Font(bold=True, color='FFFFFF')
    hdr_fill = PatternFill(start_color='A7A3AB', end_color='A7A3AB', fill_type='solid')
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal='center')

    unidades = Unidade.objects.select_related('bloco__empreendimento').order_by(
        'bloco__empreendimento__nome', 'bloco__nome', 'ordem', 'numero'
    )
    for row, u in enumerate(unidades, 2):
        ws.cell(row=row, column=1,  value=u.bloco.empreendimento.nome)
        ws.cell(row=row, column=2,  value=u.bloco.nome)
        ws.cell(row=row, column=3,  value=u.ordem)
        ws.cell(row=row, column=4,  value=u.numero)
        ws.cell(row=row, column=5,  value=u.numeros_adicionais)
        ws.cell(row=row, column=6,  value=u.get_tipo_display())
        ws.cell(row=row, column=7,  value=u.tipologia)
        ws.cell(row=row, column=8,  value=u.localizacao)
        ws.cell(row=row, column=9,  value=float(u.area_privativa))
        ws.cell(row=row, column=10, value=float(u.area_privativa_acessoria))
        ws.cell(row=row, column=11, value=float(u.area_comum))
        ws.cell(row=row, column=12, value=float(u.fracao_ideal))
        ws.cell(row=row, column=13, value=float(u.valor_tabela))
        ws.cell(row=row, column=14, value=u.get_status_display())
        ws.cell(row=row, column=15, value=u.descricao1)
        ws.cell(row=row, column=16, value=u.descricao2)
        ws.cell(row=row, column=17, value=u.descricao3)

    for col in ws.columns:
        width = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(width + 3, 40)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="unidades_{date.today().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response


@login_required
def empreendimento_csv_template(request):
    import csv as csv_mod
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="template_unidades.csv"'
    response.write('﻿')  # BOM para Excel reconhecer UTF-8
    writer = csv_mod.writer(response, delimiter=';')
    writer.writerow([
        'bloco', 'numero', 'tipo', 'tipologia', 'localizacao',
        'area_privativa', 'area_privativa_acessoria', 'area_comum',
        'fracao_ideal', 'valor_tabela', 'status',
        'descricao1', 'descricao2', 'descricao3',
    ])
    writer.writerow([
        'Torre A', '101', 'apartamento', '3D', '10º andar',
        '89.50', '0', '12.30', '0.001200', '650000.00', 'disponivel',
        '', '', '',
    ])
    writer.writerow([
        'Subsolo', 'G-01', 'garagem', 'coberta', 'Subsolo',
        '12.00', '0', '0', '0.000120', '45000.00', 'disponivel',
        '', '', '',
    ])
    return response


@login_required
def empreendimento_import_csv(request):
    import csv as csv_mod, io
    from decimal import Decimal, InvalidOperation

    if request.method != 'POST':
        return redirect('incorporadora:empreendimento_list')

    empreendimento_pk = request.POST.get('empreendimento')
    csv_file = request.FILES.get('arquivo')

    if not empreendimento_pk or not csv_file:
        messages.error(request, 'Selecione o empreendimento e o arquivo CSV.')
        return redirect('incorporadora:empreendimento_list')

    empreendimento = get_object_or_404(Empreendimento, pk=empreendimento_pk)

    tipo_map = {v.lower(): k for k, v in Unidade.TIPO_CHOICES}
    tipo_map.update({k: k for k, v in Unidade.TIPO_CHOICES})
    status_map = {v.lower(): k for k, v in Unidade.STATUS_CHOICES}
    status_map.update({k: k for k, v in Unidade.STATUS_CHOICES})

    def to_decimal(val, field, linha, erros):
        val = str(val).strip().replace(',', '.')
        try:
            return Decimal(val) if val else Decimal('0')
        except InvalidOperation:
            erros.append(f'Linha {linha}: campo "{field}" inválido ({val!r}).')
            return None

    try:
        decoded = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        csv_file.seek(0)
        decoded = csv_file.read().decode('latin-1')

    reader = csv_mod.DictReader(io.StringIO(decoded), delimiter=';')
    rows = [{k.strip().lower(): (v or '').strip() for k, v in row.items()} for row in reader]

    erros = []
    criados = 0
    blocos_cache = {}

    for i, row in enumerate(rows, 2):
        if not any(row.values()):
            continue

        bloco_nome = row.get('bloco', '').strip()
        numero = row.get('numero', '').strip()

        if not bloco_nome:
            erros.append(f'Linha {i}: coluna "bloco" obrigatória.')
            continue
        if not numero:
            erros.append(f'Linha {i}: coluna "numero" obrigatória.')
            continue

        if bloco_nome not in blocos_cache:
            bloco, _ = Bloco.objects.get_or_create(empreendimento=empreendimento, nome=bloco_nome)
            blocos_cache[bloco_nome] = bloco

        tipo_raw = row.get('tipo', 'apartamento').lower()
        tipo = tipo_map.get(tipo_raw)
        if not tipo:
            erros.append(f'Linha {i}: tipo "{tipo_raw}" inválido. Use: {", ".join(k for k,_ in Unidade.TIPO_CHOICES)}.')
            continue

        status_raw = row.get('status', 'disponivel').lower()
        status = status_map.get(status_raw, 'disponivel')

        area_priv  = to_decimal(row.get('area_privativa', '0'),           'area_privativa',           i, erros)
        area_acess = to_decimal(row.get('area_privativa_acessoria', '0'), 'area_privativa_acessoria', i, erros)
        area_comum = to_decimal(row.get('area_comum', '0'),               'area_comum',               i, erros)
        fracao     = to_decimal(row.get('fracao_ideal', '0'),             'fracao_ideal',             i, erros)
        valor      = to_decimal(row.get('valor_tabela', '0'),             'valor_tabela',             i, erros)

        if None in (area_priv, area_acess, area_comum, fracao, valor):
            continue

        Unidade.objects.update_or_create(
            bloco=blocos_cache[bloco_nome],
            numero=numero,
            defaults={
                'tipo':                     tipo,
                'tipologia':                row.get('tipologia', ''),
                'localizacao':              row.get('localizacao', ''),
                'descricao1':               row.get('descricao1', ''),
                'descricao2':               row.get('descricao2', ''),
                'descricao3':               row.get('descricao3', ''),
                'area_privativa':           area_priv,
                'area_privativa_acessoria': area_acess,
                'area_comum':               area_comum,
                'fracao_ideal':             fracao,
                'valor_tabela':             valor,
                'status':                   status,
            }
        )
        criados += 1

    if erros:
        for e in erros[:10]:
            messages.warning(request, e)
        if len(erros) > 10:
            messages.warning(request, f'... e mais {len(erros) - 10} erro(s) não exibidos.')

    if criados:
        messages.success(request, f'{criados} unidade(s) importada(s)/atualizadas em "{empreendimento}".')
    elif not erros:
        messages.warning(request, 'Nenhuma unidade encontrada no arquivo.')

    return redirect('incorporadora:empreendimento_list')


@login_required
def empreendimento_relatorio_pdf(request, pk):
    from decimal import Decimal
    from io import BytesIO
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT

    empreendimento = get_object_or_404(
        Empreendimento.objects.select_related('empresa'), pk=pk
    )
    blocos = empreendimento.blocos.prefetch_related('unidades').order_by('nome')

    zero = Decimal('0')
    campos = ['area_privativa', 'area_privativa_acessoria', 'area_comum', 'fracao_ideal', 'valor_tabela']

    def calcular_totais(uns):
        return {c: sum((getattr(u, c) for u in uns), zero) for c in campos}

    blocos_data = []
    for bloco in blocos:
        uns = list(bloco.unidades.all())
        blocos_data.append({'bloco': bloco, 'unidades': uns, 'totais': calcular_totais(uns)})
    todas = [u for b in blocos_data for u in b['unidades']]

    # ── cores ──
    C_HDR   = colors.HexColor('#A7A3AB')
    C_ALT   = colors.HexColor('#f7f7f7')
    C_SUB   = colors.HexColor('#f0eff2')
    C_BORDA = colors.HexColor('#e0e0e0')
    C_WHITE = colors.white

    # ── estilos de parágrafo ──
    def ps(name, font='Helvetica', size=8.5, color=colors.black, align=TA_LEFT, **kw):
        return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color, alignment=align, **kw)

    sN  = ps('n')
    sR  = ps('r',  align=TA_RIGHT)
    sB  = ps('b',  font='Helvetica-Bold')
    sBR = ps('br', font='Helvetica-Bold', align=TA_RIGHT)
    sH  = ps('h',  font='Helvetica-Bold', size=8, color=C_WHITE)
    sHR = ps('hr', font='Helvetica-Bold', size=8, color=C_WHITE, align=TA_RIGHT)
    sSL = ps('sl', font='Helvetica-Bold', size=8)
    sSR = ps('sr', font='Helvetica-Bold', size=8, align=TA_RIGHT)
    sTL = ps('tl', font='Helvetica-Bold', size=9,  color=C_WHITE)
    sTR = ps('tr', font='Helvetica-Bold', size=9,  color=C_WHITE, align=TA_RIGHT)

    # ── larguras das colunas (total = 267mm) ──
    # Nº | Tipo | Tipologia | Localização | ÁPriv | ÁAcess | ÁComum | Fração | Valor | Status
    CW = [17*mm, 20*mm, 35*mm, 38*mm, 23*mm, 29*mm, 23*mm, 24*mm, 30*mm, 28*mm]
    # 11+26+35+38+23+29+23+24+30+28 = 267mm

    def fmt_dec(v, places=2):
        return f'{float(v):.{places}f}'

    def hdr_row():
        return [
            Paragraph('Nº', sH),
            Paragraph('Tipo', sH),
            Paragraph('Tipologia', sH),
            Paragraph('Localização', sH),
            Paragraph('Área Priv. (m²)', sHR),
            Paragraph('Área Priv. Acess. (m²)', sHR),
            Paragraph('Área Comum (m²)', sHR),
            Paragraph('Fração Ideal', sHR),
            Paragraph('Valor Tabela (R$)', sHR),
            Paragraph('Status', sH),
        ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    els = []

    # cabeçalho do documento
    els.append(Paragraph(empreendimento.empresa.razao_social.upper(),
                         ps('emp', font='Helvetica-Bold', size=10, color=C_HDR)))
    els.append(Paragraph(f'Relatório de Unidades — {empreendimento.nome}',
                         ps('tit', font='Helvetica-Bold', size=14, color=colors.HexColor('#1a1a2e'),
                            spaceBefore=4)))
    els.append(Paragraph(
        f'{empreendimento.empresa} — {empreendimento.get_status_display()} — Gerado em {date.today().strftime("%d/%m/%Y")}',
        ps('sub', size=8, color=colors.HexColor('#666666'), spaceBefore=5)))
    els.append(HRFlowable(width='100%', thickness=2, color=C_HDR, spaceAfter=6*mm, spaceBefore=2*mm))

    for item in blocos_data:
        bloco = item['bloco']
        uns   = item['unidades']
        tots  = item['totais']

        els.append(Paragraph(f'Bloco: {bloco.nome}',
                             ps('bn', font='Helvetica-Bold', size=9,
                                color=colors.HexColor('#1a1a2e'), spaceBefore=6*mm, spaceAfter=2*mm)))
        if not uns:
            continue

        data = [hdr_row()]
        for u in uns:
            data.append([
                Paragraph(u.numero_display, sB),
                Paragraph(u.get_tipo_display(), sN),
                Paragraph(u.tipologia or '', sN),
                Paragraph(u.localizacao or '', sN),
                Paragraph(fmt_dec(u.area_privativa), sR),
                Paragraph(fmt_dec(u.area_privativa_acessoria), sR),
                Paragraph(fmt_dec(u.area_comum), sR),
                Paragraph(fmt_dec(u.fracao_ideal, 6), sR),
                Paragraph(fmt_dec(u.valor_tabela), sR),
                Paragraph(u.get_status_display(), sN),
            ])
        # subtotal
        data.append([
            Paragraph(f'Subtotal — {bloco.nome}', sSL), '', '', '',
            Paragraph(fmt_dec(tots['area_privativa']), sSR),
            Paragraph(fmt_dec(tots['area_privativa_acessoria']), sSR),
            Paragraph(fmt_dec(tots['area_comum']), sSR),
            Paragraph(fmt_dec(tots['fracao_ideal'], 6), sSR),
            Paragraph(fmt_dec(tots['valor_tabela']), sSR),
            '',
        ])

        nr = len(data)
        ts = TableStyle([
            ('BACKGROUND',  (0, 0),  (-1, 0),   C_HDR),
            ('ROWBACKGROUNDS', (0, 1), (-1, nr-2), [C_WHITE, C_ALT]),
            ('BACKGROUND',  (0, -1), (-1, -1),  C_SUB),
            ('LINEBELOW',   (0, 1),  (-1, nr-2), 0.5, C_BORDA),
            ('LINEABOVE',   (0, -1), (-1, -1),   1,   C_HDR),
            ('SPAN',        (0, -1), (3, -1)),
            ('VALIGN',      (0, 0),  (-1, -1),  'MIDDLE'),
            ('LEFTPADDING',  (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING',   (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ])
        t = Table(data, colWidths=CW, repeatRows=1)
        t.setStyle(ts)
        els.append(t)
        els.append(Spacer(1, 4*mm))

    # total geral
    if todas:
        tg = calcular_totais(todas)
        tdata = [[
            Paragraph(f'TOTAL GERAL — {len(todas)} unidade(s)', sTL), '', '', '',
            Paragraph(fmt_dec(tg['area_privativa']), sTR),
            Paragraph(fmt_dec(tg['area_privativa_acessoria']), sTR),
            Paragraph(fmt_dec(tg['area_comum']), sTR),
            Paragraph(fmt_dec(tg['fracao_ideal'], 6), sTR),
            Paragraph(fmt_dec(tg['valor_tabela']), sTR),
            '',
        ]]
        tt = Table(tdata, colWidths=CW)
        tt.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, 0), C_HDR),
            ('SPAN',         (0, 0), (3, 0)),
            ('LINEABOVE',    (0, 0), (-1, 0), 2, C_HDR),
            ('VALIGN',       (0, 0), (-1, 0), 'MIDDLE'),
            ('LEFTPADDING',  (0, 0), (-1, 0), 4),
            ('RIGHTPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING',   (0, 0), (-1, 0), 5),
            ('BOTTOMPADDING',(0, 0), (-1, 0), 5),
        ]))
        els.append(tt)

    doc.build(els)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="relatorio_{pk}.pdf"'
    return response


@login_required
def vinculo_list(request, bloco_pk):
    bloco = get_object_or_404(Bloco.objects.select_related('empreendimento'), pk=bloco_pk)

    principais = (
        bloco.unidades
        .filter(tipo__in=['apartamento', 'sala', 'loja'])
        .prefetch_related('vinculadas')
        .order_by('ordem', 'numero')
    )

    def _split_aliases(u):
        """Separa aliases em HB (hobby_box) e outros (garagem/moto/etc)."""
        if not u.numeros_adicionais:
            return [], []
        parts = [a.strip() for a in u.numeros_adicionais.split(',') if a.strip()]
        hb    = [a for a in parts if a.upper().startswith('HB')]
        outros = [a for a in parts if not a.upper().startswith('HB')]
        return outros, hb

    def _display(numero, aliases):
        if not aliases:
            return numero
        return f'{numero} ({" · ".join(aliases)})'

    rows = []
    for u in principais:
        vinculadas = list(u.vinculadas.all())
        garagens = []
        hbs      = []
        outros   = []

        for v in vinculadas:
            outros_aliases, hb_aliases = _split_aliases(v)
            if v.tipo == 'garagem':
                sufixo = '*' if hb_aliases else ''
                garagens.append(_display(v.numero, outros_aliases) + sufixo)
                hbs.extend(hb_aliases)
            elif v.tipo == 'hobby_box':
                hbs.append(_display(v.numero, outros_aliases))
            else:
                outros.append(_display(v.numero, outros_aliases + hb_aliases))

        if vinculadas:
            rows.append({'unidade': u, 'garagens': garagens, 'hbs': hbs, 'outros': outros})

    sem_vinculo = bloco.unidades.filter(
        tipo__in=['garagem', 'hobby_box'],
        unidade_principal__isnull=True,
    ).order_by('tipo', 'ordem', 'numero')

    return render(request, 'incorporadora/vinculo_list.html', {
        'bloco':       bloco,
        'rows':        rows,
        'sem_vinculo': sem_vinculo,
    })


@login_required
def vinculo_csv_template(request, bloco_pk):
    import csv as csv_mod
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="template_vinculos.csv"'
    response.write('﻿')
    writer = csv_mod.writer(response, delimiter=';')
    writer.writerow(['unidade', 'vinculada'])
    writer.writerow(['201', 'G57'])
    writer.writerow(['201', 'HB65'])
    writer.writerow(['202', 'G18'])
    writer.writerow(['202', 'HB13'])
    return response


@login_required
def vinculo_import_csv(request, bloco_pk):
    import csv as csv_mod, io

    bloco = get_object_or_404(Bloco.objects.select_related('empreendimento'), pk=bloco_pk)

    if request.method != 'POST':
        return redirect('incorporadora:vinculo_list', bloco_pk=bloco_pk)

    csv_file = request.FILES.get('arquivo')
    if not csv_file:
        messages.error(request, 'Selecione um arquivo CSV.')
        return redirect('incorporadora:vinculo_list', bloco_pk=bloco_pk)

    try:
        decoded = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        csv_file.seek(0)
        decoded = csv_file.read().decode('latin-1')

    reader = csv_mod.DictReader(io.StringIO(decoded), delimiter=';')
    rows = [{k.strip().lower(): (v or '').strip() for k, v in row.items()} for row in reader]

    todas_unidades = list(bloco.unidades.all())
    unidades_bloco = {u.numero: u for u in todas_unidades}

    def buscar_unidade(numero):
        if numero in unidades_bloco:
            return unidades_bloco[numero]
        for u in todas_unidades:
            if u.numeros_adicionais:
                aliases = [a.strip() for a in u.numeros_adicionais.split(',') if a.strip()]
                if numero in aliases:
                    return u
        return None

    erros = []
    vinculados = 0

    for i, row in enumerate(rows, 2):
        if not any(row.values()):
            continue

        num_principal = row.get('unidade', '').strip()
        num_vinculada = row.get('vinculada', '').strip()

        if not num_principal or not num_vinculada:
            erros.append(f'Linha {i}: colunas "unidade" e "vinculada" são obrigatórias.')
            continue

        principal = buscar_unidade(num_principal)
        if not principal:
            erros.append(f'Linha {i}: unidade "{num_principal}" não encontrada no bloco.')
            continue

        vinculada = buscar_unidade(num_vinculada)
        if not vinculada:
            erros.append(f'Linha {i}: unidade "{num_vinculada}" não encontrada no bloco.')
            continue

        if vinculada.pk == principal.pk:
            erros.append(f'Linha {i}: uma unidade não pode ser vinculada a si mesma.')
            continue

        vinculada.unidade_principal = principal
        vinculada.save(update_fields=['unidade_principal'])
        vinculados += 1

    if erros:
        for e in erros[:10]:
            messages.warning(request, e)
        if len(erros) > 10:
            messages.warning(request, f'... e mais {len(erros) - 10} erro(s) não exibidos.')

    if vinculados:
        messages.success(request, f'{vinculados} vínculo(s) importado(s) em "{bloco.nome}".')
    elif not erros:
        messages.warning(request, 'Nenhum vínculo encontrado no arquivo.')

    return redirect('incorporadora:vinculo_list', bloco_pk=bloco_pk)


@login_required
def unidade_export_excel(request, bloco_pk):
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    bloco = get_object_or_404(Bloco.objects.select_related('empreendimento'), pk=bloco_pk)
    unidades = bloco.unidades.all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Unidades'

    headers = [
        'Ordem', 'Número', 'Números Adicionais', 'Tipo', 'Tipologia', 'Localização',
        'Área Privativa (m²)', 'Área Priv. Acess. (m²)', 'Área Comum (m²)',
        'Fração Ideal', 'Valor Tabela (R$)', 'Status',
        'Descrição 1', 'Descrição 2', 'Descrição 3',
    ]
    hdr_font = Font(bold=True, color='FFFFFF')
    hdr_fill = PatternFill(start_color='A7A3AB', end_color='A7A3AB', fill_type='solid')
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = hdr_font
        cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal='center')

    for row, u in enumerate(unidades, 2):
        ws.cell(row=row, column=1,  value=u.ordem)
        ws.cell(row=row, column=2,  value=u.numero)
        ws.cell(row=row, column=3,  value=u.numeros_adicionais)
        ws.cell(row=row, column=4,  value=u.get_tipo_display())
        ws.cell(row=row, column=5,  value=u.tipologia)
        ws.cell(row=row, column=6,  value=u.localizacao)
        ws.cell(row=row, column=7,  value=float(u.area_privativa))
        ws.cell(row=row, column=8,  value=float(u.area_privativa_acessoria))
        ws.cell(row=row, column=9,  value=float(u.area_comum))
        ws.cell(row=row, column=10, value=float(u.fracao_ideal))
        ws.cell(row=row, column=11, value=float(u.valor_tabela))
        ws.cell(row=row, column=12, value=u.get_status_display())
        ws.cell(row=row, column=13, value=u.descricao1)
        ws.cell(row=row, column=14, value=u.descricao2)
        ws.cell(row=row, column=15, value=u.descricao3)

    for col in ws.columns:
        width = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(width + 3, 40)

    nome_bloco = bloco.nome.replace(' ', '_')
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="unidades_{nome_bloco}_{date.today().strftime("%Y%m%d")}.xlsx"'
    wb.save(response)
    return response


@login_required
def unidade_csv_template(request, bloco_pk):
    import csv as csv_mod
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="template_unidades.csv"'
    response.write('﻿')
    writer = csv_mod.writer(response, delimiter=';')
    writer.writerow([
        'ordem', 'numero', 'numeros_adicionais', 'tipo', 'tipologia', 'localizacao',
        'area_privativa', 'area_privativa_acessoria', 'area_comum',
        'fracao_ideal', 'valor_tabela', 'status',
        'descricao1', 'descricao2', 'descricao3',
    ])
    writer.writerow([
        '1', '101', '', 'apartamento', '3D', '10º andar',
        '89.50', '0', '12.30', '0.001200', '650000.00', 'disponivel',
        '', '', '',
    ])
    writer.writerow([
        '2', 'G01', 'M03,HB60', 'garagem', 'coberta', 'Subsolo',
        '12.00', '0', '0', '0.000120', '45000.00', 'disponivel',
        '', '', '',
    ])
    return response


@login_required
def unidade_import_csv(request, bloco_pk):
    import csv as csv_mod, io
    from decimal import Decimal, InvalidOperation

    bloco = get_object_or_404(Bloco.objects.select_related('empreendimento'), pk=bloco_pk)

    if request.method != 'POST':
        return redirect('incorporadora:unidade_list', bloco_pk=bloco_pk)

    csv_file = request.FILES.get('arquivo')
    if not csv_file:
        messages.error(request, 'Selecione um arquivo CSV.')
        return redirect('incorporadora:unidade_list', bloco_pk=bloco_pk)

    tipo_map = {v.lower(): k for k, v in Unidade.TIPO_CHOICES}
    tipo_map.update({k: k for k, v in Unidade.TIPO_CHOICES})
    status_map = {v.lower(): k for k, v in Unidade.STATUS_CHOICES}
    status_map.update({k: k for k, v in Unidade.STATUS_CHOICES})

    def to_decimal(val, field, linha, erros):
        val = str(val).strip().replace(',', '.')
        try:
            return Decimal(val) if val else Decimal('0')
        except InvalidOperation:
            erros.append(f'Linha {linha}: campo "{field}" inválido ({val!r}).')
            return None

    try:
        decoded = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        csv_file.seek(0)
        decoded = csv_file.read().decode('latin-1')

    reader = csv_mod.DictReader(io.StringIO(decoded), delimiter=';')
    rows = [{k.strip().lower(): (v or '').strip() for k, v in row.items()} for row in reader]

    erros = []
    criados = 0

    for i, row in enumerate(rows, 2):
        if not any(row.values()):
            continue

        numero = row.get('numero', '').strip()
        if not numero:
            erros.append(f'Linha {i}: coluna "numero" obrigatória.')
            continue

        tipo_raw = row.get('tipo', 'apartamento').lower()
        tipo = tipo_map.get(tipo_raw)
        if not tipo:
            erros.append(f'Linha {i}: tipo "{tipo_raw}" inválido. Use: {", ".join(k for k,_ in Unidade.TIPO_CHOICES)}.')
            continue

        status_raw = row.get('status', 'disponivel').lower()
        status = status_map.get(status_raw, 'disponivel')

        try:
            ordem = int(row.get('ordem', '0') or '0')
        except ValueError:
            ordem = 0

        area_priv  = to_decimal(row.get('area_privativa', '0'),           'area_privativa',           i, erros)
        area_acess = to_decimal(row.get('area_privativa_acessoria', '0'), 'area_privativa_acessoria', i, erros)
        area_com   = to_decimal(row.get('area_comum', '0'),               'area_comum',               i, erros)
        fracao     = to_decimal(row.get('fracao_ideal', '0'),             'fracao_ideal',             i, erros)
        valor      = to_decimal(row.get('valor_tabela', '0'),             'valor_tabela',             i, erros)

        if None in (area_priv, area_acess, area_com, fracao, valor):
            continue

        Unidade.objects.update_or_create(
            bloco=bloco,
            numero=numero,
            defaults={
                'ordem':                    ordem,
                'numeros_adicionais':       row.get('numeros_adicionais', ''),
                'tipo':                     tipo,
                'tipologia':                row.get('tipologia', ''),
                'localizacao':              row.get('localizacao', ''),
                'area_privativa':           area_priv,
                'area_privativa_acessoria': area_acess,
                'area_comum':               area_com,
                'fracao_ideal':             fracao,
                'valor_tabela':             valor,
                'status':                   status,
                'descricao1':               row.get('descricao1', ''),
                'descricao2':               row.get('descricao2', ''),
                'descricao3':               row.get('descricao3', ''),
            }
        )
        criados += 1

    if erros:
        for e in erros[:10]:
            messages.warning(request, e)
        if len(erros) > 10:
            messages.warning(request, f'... e mais {len(erros) - 10} erro(s) não exibidos.')

    if criados:
        messages.success(request, f'{criados} unidade(s) importada(s)/atualizadas em "{bloco.nome}".')
    elif not erros:
        messages.warning(request, 'Nenhuma unidade encontrada no arquivo.')

    return redirect('incorporadora:unidade_list', bloco_pk=bloco_pk)


@login_required
def empresa_list_pdf(request):
    empresas = Empresa.objects.all()
    primeira = empresas.filter(ativo=True).first()
    return render_to_pdf('incorporadora/pdf/empresa_list.html', {
        'empresas': empresas,
        'empresa_nome': primeira.razao_social if primeira else '',
        'data': date.today().strftime('%d/%m/%Y'),
    }, filename='empresas.pdf')


@login_required
def empreendimento_list_pdf(request):
    empreendimentos = Empreendimento.objects.select_related('empresa').all()
    primeira = Empresa.objects.filter(ativo=True).first()
    return render_to_pdf('incorporadora/pdf/empreendimento_list.html', {
        'empreendimentos': empreendimentos,
        'empresa_nome': primeira.razao_social if primeira else '',
        'data': date.today().strftime('%d/%m/%Y'),
    }, filename='empreendimentos.pdf')


@login_required
def bloco_list_pdf(request, empreendimento_pk):
    empreendimento = get_object_or_404(Empreendimento.objects.select_related('empresa'), pk=empreendimento_pk)
    blocos = list(empreendimento.blocos.all())
    return render_to_pdf('incorporadora/pdf/bloco_list.html', {
        'empreendimento': empreendimento,
        'blocos': blocos,
        'empresa_nome': empreendimento.empresa.razao_social,
        'data': date.today().strftime('%d/%m/%Y'),
    }, filename=f'blocos_{empreendimento.pk}.pdf')


@login_required
def unidade_list_pdf(request, bloco_pk):
    from io import BytesIO
    from decimal import Decimal
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT

    bloco = get_object_or_404(Bloco.objects.select_related('empreendimento__empresa'), pk=bloco_pk)
    unidades = list(bloco.unidades.all())

    zero = Decimal('0')
    campos = ['area_privativa', 'area_privativa_acessoria', 'area_comum', 'fracao_ideal', 'valor_tabela']
    tots = {c: sum((getattr(u, c) for u in unidades), zero) for c in campos}

    C_HDR   = colors.HexColor('#A7A3AB')
    C_ALT   = colors.HexColor('#f7f7f7')
    C_SUB   = colors.HexColor('#f0eff2')
    C_BORDA = colors.HexColor('#e0e0e0')
    C_WHITE = colors.white

    def ps(name, font='Helvetica', size=8.5, color=colors.black, align=TA_LEFT, **kw):
        return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color, alignment=align, **kw)

    sN  = ps('n')
    sR  = ps('r',  align=TA_RIGHT)
    sB  = ps('b',  font='Helvetica-Bold')
    sBR = ps('br', font='Helvetica-Bold', align=TA_RIGHT)
    sH  = ps('h',  font='Helvetica-Bold', size=8, color=C_WHITE)
    sHR = ps('hr', font='Helvetica-Bold', size=8, color=C_WHITE, align=TA_RIGHT)
    sTL = ps('tl', font='Helvetica-Bold', size=9, color=C_WHITE)
    sTR = ps('tr', font='Helvetica-Bold', size=9, color=C_WHITE, align=TA_RIGHT)

    CW = [17*mm, 20*mm, 35*mm, 38*mm, 23*mm, 29*mm, 23*mm, 24*mm, 30*mm, 28*mm]

    def fmt_dec(v, places=2):
        return f'{float(v):.{places}f}'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    els = []

    emp = bloco.empreendimento
    els.append(Paragraph(emp.empresa.razao_social.upper(),
                         ps('emp', font='Helvetica-Bold', size=10, color=C_HDR)))
    els.append(Paragraph(f'Relatório de Unidades — {emp.nome}',
                         ps('tit', font='Helvetica-Bold', size=14, color=colors.HexColor('#1a1a2e'),
                            spaceBefore=4)))
    els.append(Paragraph(
        f'Bloco: {bloco.nome} — {emp.get_status_display()} — Gerado em {date.today().strftime("%d/%m/%Y")}',
        ps('sub', size=8, color=colors.HexColor('#666666'), spaceBefore=5)))
    els.append(HRFlowable(width='100%', thickness=2, color=C_HDR, spaceAfter=6*mm, spaceBefore=2*mm))

    data = [[
        Paragraph('Nº', sH),
        Paragraph('Tipo', sH),
        Paragraph('Tipologia', sH),
        Paragraph('Localização', sH),
        Paragraph('Área Priv. (m²)', sHR),
        Paragraph('Área Priv. Acess. (m²)', sHR),
        Paragraph('Área Comum (m²)', sHR),
        Paragraph('Fração Ideal', sHR),
        Paragraph('Valor Tabela (R$)', sHR),
        Paragraph('Status', sH),
    ]]
    for u in unidades:
        data.append([
            Paragraph(u.numero_display, sB),
            Paragraph(u.get_tipo_display(), sN),
            Paragraph(u.tipologia or '', sN),
            Paragraph(u.localizacao or '', sN),
            Paragraph(fmt_dec(u.area_privativa), sR),
            Paragraph(fmt_dec(u.area_privativa_acessoria), sR),
            Paragraph(fmt_dec(u.area_comum), sR),
            Paragraph(fmt_dec(u.fracao_ideal, 6), sR),
            Paragraph(fmt_dec(u.valor_tabela), sR),
            Paragraph(u.get_status_display(), sN),
        ])

    if unidades:
        sSL = ps('sl', font='Helvetica-Bold', size=8)
        sSR = ps('sr', font='Helvetica-Bold', size=8, align=TA_RIGHT)
        data.append([
            Paragraph(f'Total — {len(unidades)} unidade(s)', sSL), '', '', '',
            Paragraph(fmt_dec(tots['area_privativa']), sSR),
            Paragraph(fmt_dec(tots['area_privativa_acessoria']), sSR),
            Paragraph(fmt_dec(tots['area_comum']), sSR),
            Paragraph(fmt_dec(tots['fracao_ideal'], 6), sSR),
            Paragraph(fmt_dec(tots['valor_tabela']), sSR),
            '',
        ])

    nr = len(data)
    ts = TableStyle([
        ('BACKGROUND',   (0, 0),  (-1, 0),   C_HDR),
        ('ROWBACKGROUNDS', (0, 1), (-1, nr-2 if unidades else -1), [C_WHITE, C_ALT]),
        ('BACKGROUND',   (0, -1), (-1, -1),  C_SUB),
        ('LINEBELOW',    (0, 1),  (-1, nr-2), 0.5, C_BORDA),
        ('LINEABOVE',    (0, -1), (-1, -1),   1,   C_HDR),
        ('SPAN',         (0, -1), (3, -1)),
        ('VALIGN',       (0, 0),  (-1, -1),  'MIDDLE'),
        ('LEFTPADDING',  (0, 0),  (-1, -1),  4),
        ('RIGHTPADDING', (0, 0),  (-1, -1),  4),
        ('TOPPADDING',   (0, 0),  (-1, -1),  3),
        ('BOTTOMPADDING',(0, 0),  (-1, -1),  3),
    ])
    t = Table(data, colWidths=CW, repeatRows=1)
    t.setStyle(ts)
    els.append(t)

    doc.build(els)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="unidades_{bloco_pk}.pdf"'
    return response
