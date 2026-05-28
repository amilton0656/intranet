import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.incorporadora.models import Empreendimento, TabelaVendas, Unidade, SeriePagamento, ValorSerie
from apps.pessoas.models import Pessoa

from .models import (
    Proposta, UnidadeProposta, ParticipanteProposta,
    SerieProposta, DocumentoProposta,
)


# ── helpers ───────────────────────────────────────────────────────────────────

_INDICE_MAP = {
    'cub':  'cub_residencial',
    'igpm': 'igpm',
    'fixo': 'nenhum',
}


def _copiar_series_da_tabela(proposta, unidade=None):
    """Recria séries de tabela e proposta usando ValorSerie da unidade."""
    if unidade is None:
        up = proposta.unidades.select_related('unidade').first()
        if up:
            unidade = up.unidade

    vs_map = {}
    if unidade:
        for vs in ValorSerie.objects.filter(
            item__tabela=proposta.tabela,
            item__unidade=unidade,
        ).select_related('serie'):
            vs_map[vs.serie_id] = vs.valor_parcela

    proposta.series.filter(origem__in=['tabela', 'proposta']).delete()
    bulk = []
    for i, s in enumerate(proposta.tabela.series.order_by('ordem')):
        valor = vs_map.get(s.pk, 0)
        kwargs = dict(
            proposta=proposta,
            label=s.get_tipo_display(),
            tipo='fixa',
            quantidade=s.quantidade or 1,
            valor=valor,
            primeiro_vencimento=s.primeiro_vencimento,
            indexador=_INDICE_MAP.get(s.indice, 'nenhum'),
            ordem=i,
        )
        bulk.append(SerieProposta(origem='tabela', **kwargs))
        bulk.append(SerieProposta(origem='proposta', **kwargs))
    SerieProposta.objects.bulk_create(bulk)


def _get_proposta(numero):
    return get_object_or_404(
        Proposta.objects
        .select_related('imobiliaria', 'corretor', 'empreendimento', 'tabela')
        .prefetch_related(
            'unidades__unidade__bloco',
            'participantes__pessoa',
            'series',
            'documentos__participante__pessoa',
        ),
        numero=numero,
    )


SITUACAO_CORES = {
    'rascunho':           '#6c757d',
    'enviada':            '#0d6efd',
    'em_analise':         '#0ea5e9',
    'aprovada':           '#198754',
    'reprovada':          '#dc3545',
    'contrato_elaborado': '#6f42c1',
    'contratada':         '#0f766e',
}


def _etapas_choices():
    from .models import WorkflowEtapa
    qs = list(WorkflowEtapa.objects.order_by('ordem').values_list('slug', 'label'))
    return qs if qs else Proposta.SITUACAO_CHOICES


def _etapas_map():
    from .models import WorkflowEtapa
    return {e.slug: {'label': e.label, 'cor': e.cor}
            for e in WorkflowEtapa.objects.all()}


def _build_drawflow():
    from .models import WorkflowEtapa, WorkflowTransicao
    etapas = list(WorkflowEtapa.objects.order_by('ordem'))
    if not etapas:
        return _default_drawflow()
    slug_to_id = {e.slug: str(i + 1) for i, e in enumerate(etapas)}
    nodes = {}
    for i, e in enumerate(etapas):
        nid = str(i + 1)
        nodes[nid] = {
            'id': i + 1,
            'name': e.slug,
            'data': {},
            'class': e.slug,
            'html': f'<div class="wf-node-header" style="background:{e.cor}">{e.label}</div>',
            'typenode': False,
            'inputs':  {'input_1':  {'connections': []}},
            'outputs': {'output_1': {'connections': []}},
            'pos_x': e.pos_x,
            'pos_y': e.pos_y,
        }
    for t in WorkflowTransicao.objects.select_related('de_etapa', 'para_etapa'):
        src = slug_to_id.get(t.de_etapa.slug)
        dst = slug_to_id.get(t.para_etapa.slug)
        if src and dst:
            nodes[src]['outputs']['output_1']['connections'].append({'node': dst, 'output': 'output_1'})
            nodes[dst]['inputs']['input_1']['connections'].append({'node': src, 'input': 'input_1'})
    return {'drawflow': {'Home': {'data': nodes}}}


def _sync_from_drawflow(data):
    from collections import defaultdict, deque
    from .models import WorkflowEtapa, WorkflowTransicao

    nodes = data.get('drawflow', {}).get('Home', {}).get('data', {})

    # Update node positions
    for node in nodes.values():
        slug = node.get('name', '')
        if slug:
            WorkflowEtapa.objects.filter(slug=slug).update(
                pos_x=node.get('pos_x', 100),
                pos_y=node.get('pos_y', 100),
            )

    # Rebuild transitions
    WorkflowTransicao.objects.all().delete()
    seen = set()
    for nid, node in nodes.items():
        src_slug = node.get('name', '')
        for conn in node.get('outputs', {}).get('output_1', {}).get('connections', []):
            dst_nid = conn.get('node')
            if dst_nid in nodes:
                dst_slug = nodes[dst_nid].get('name', '')
                pair = (src_slug, dst_slug)
                if src_slug and dst_slug and pair not in seen:
                    seen.add(pair)
                    try:
                        WorkflowTransicao.objects.create(
                            de_etapa=WorkflowEtapa.objects.get(slug=src_slug),
                            para_etapa=WorkflowEtapa.objects.get(slug=dst_slug),
                        )
                    except WorkflowEtapa.DoesNotExist:
                        pass

    # Topological sort → update `ordem` so Kanban columns follow workflow order
    etapas = list(WorkflowEtapa.objects.all())
    transicoes = list(WorkflowTransicao.objects.select_related('de_etapa', 'para_etapa'))

    adj = defaultdict(list)
    in_deg = {e.slug: 0 for e in etapas}
    for t in transicoes:
        adj[t.de_etapa.slug].append(t.para_etapa.slug)
        in_deg[t.para_etapa.slug] += 1

    # Start with source nodes (no incoming edges), sorted for determinism
    queue = deque(sorted(s for s, d in in_deg.items() if d == 0))
    ordered = []
    while queue:
        slug = queue.popleft()
        ordered.append(slug)
        for nxt in sorted(adj[slug]):
            in_deg[nxt] -= 1
            if in_deg[nxt] == 0:
                queue.append(nxt)

    # Append any nodes not reached (isolated or in a cycle)
    visited = set(ordered)
    for e in etapas:
        if e.slug not in visited:
            ordered.append(e.slug)

    for i, slug in enumerate(ordered):
        WorkflowEtapa.objects.filter(slug=slug).update(ordem=i)


# ── kanban mover ─────────────────────────────────────────────────────────────

@login_required
def kanban_mover(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    try:
        from .models import WorkflowEtapa
        import logging
        logger = logging.getLogger(__name__)
        data = json.loads(request.body)
        numero = data.get('numero', '').strip()
        nova_situacao = data.get('situacao', '').strip()
        if not numero or not nova_situacao:
            return JsonResponse({'error': 'Dados inválidos'}, status=400)
        if not WorkflowEtapa.objects.filter(slug=nova_situacao).exists():
            return JsonResponse({'error': f'Etapa não encontrada: {nova_situacao}'}, status=404)
        updated = Proposta.objects.filter(numero=numero).update(situacao=nova_situacao)
        if not updated:
            return JsonResponse({'error': f'Proposta não encontrada: {numero}'}, status=404)
        return JsonResponse({'ok': True})
    except Exception as exc:
        import logging, traceback
        logging.getLogger(__name__).error('kanban_mover error: %s\n%s', exc, traceback.format_exc())
        return JsonResponse({'error': str(exc)}, status=500)


# ── listagem ──────────────────────────────────────────────────────────────────

@login_required
def proposta_list(request):
    qs = (Proposta.objects
          .select_related('imobiliaria', 'corretor', 'empreendimento', 'tabela')
          .prefetch_related('participantes__pessoa'))

    situacao = request.GET.get('situacao', '')
    if situacao:
        qs = qs.filter(situacao=situacao)

    return render(request, 'propostas/proposta_list.html', {
        'propostas':        qs,
        'situacao_filter':  situacao,
        'situacao_choices': _etapas_choices(),
        'etapas_map':       _etapas_map(),
    })


@login_required
def proposta_list_pdf(request):
    from io import BytesIO
    from decimal import Decimal
    from django.http import HttpResponse
    from django.utils import timezone
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER

    situacao = request.GET.get('situacao', '')
    qs = (Proposta.objects
          .select_related('imobiliaria', 'corretor', 'empreendimento', 'tabela')
          .prefetch_related('participantes__pessoa', 'series')
          .order_by('data', 'numero'))
    if situacao:
        qs = qs.filter(situacao=situacao)

    etapas_map = _etapas_map()

    def _brl(v):
        v = v or Decimal('0')
        s = f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f'R$ {s}'

    def _proponentes(p):
        nomes = [pt.pessoa.nome for pt in p.participantes.all() if pt.papel == 'proponente']
        return ', '.join(nomes) if nomes else '—'

    page = landscape(A4)
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=page,
        leftMargin=12*mm, rightMargin=12*mm,
        topMargin=14*mm, bottomMargin=14*mm,
    )

    titulo_style = ParagraphStyle('titulo', fontName='Helvetica-Bold', fontSize=13, spaceAfter=4)
    sub_style    = ParagraphStyle('sub',    fontName='Helvetica',      fontSize=8,  spaceAfter=8, textColor=colors.HexColor('#6c757d'))
    cell_style   = ParagraphStyle('cell',   fontName='Helvetica',      fontSize=7.5, leading=10)
    hdr_style    = ParagraphStyle('hdr',    fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.white)
    val_style    = ParagraphStyle('val',    fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=TA_RIGHT)

    titulo_label = 'Propostas'
    if situacao and situacao in etapas_map:
        titulo_label += f' — {etapas_map[situacao]["label"]}'

    els = [
        Paragraph('Propostas', titulo_style),
        Paragraph(f'Gerado em {timezone.localdate().strftime("%d/%m/%Y")}  ·  {qs.count()} registro(s)', sub_style),
    ]

    headers = ['Número', 'Data', 'Situação', 'Empreendimento', 'Imobiliária', 'Corretor', 'Proponente(s)', 'Valor Proposto']
    rows = [[Paragraph(h, hdr_style) for h in headers]]

    total_geral = Decimal('0')
    for p in qs:
        etapa = etapas_map.get(p.situacao, {})
        situacao_label = etapa.get('label', p.situacao)
        valor = p.valor_proposto_total
        total_geral += valor
        rows.append([
            Paragraph(p.numero,              cell_style),
            Paragraph(p.data.strftime('%d/%m/%Y'), cell_style),
            Paragraph(situacao_label,        cell_style),
            Paragraph(str(p.empreendimento), cell_style),
            Paragraph(str(p.imobiliaria),    cell_style),
            Paragraph(str(p.corretor),       cell_style),
            Paragraph(_proponentes(p),       cell_style),
            Paragraph(_brl(valor),           val_style),
        ])

    # linha de total
    rows.append([
        Paragraph('', cell_style),
        Paragraph('', cell_style),
        Paragraph('', cell_style),
        Paragraph('', cell_style),
        Paragraph('', cell_style),
        Paragraph('', cell_style),
        Paragraph('Total', ParagraphStyle('tot', fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=TA_RIGHT)),
        Paragraph(_brl(total_geral), ParagraphStyle('totv', fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=TA_RIGHT)),
    ])

    # larguras das colunas (landscape A4 ≈ 267mm de área útil)
    col_w = [26*mm, 20*mm, 30*mm, 44*mm, 36*mm, 36*mm, 44*mm, 31*mm]

    CINZA  = colors.HexColor('#343a40')
    LINHA  = colors.HexColor('#dee2e6')
    TOTAL  = colors.HexColor('#e8f0fe')
    n_data = len(rows)

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        # cabeçalho
        ('BACKGROUND',   (0, 0), (-1, 0),        CINZA),
        ('ROWBACKGROUNDS', (0, 1), (-1, n_data-2), [colors.white, colors.HexColor('#f8f9fa')]),
        # linha de total
        ('BACKGROUND',   (0, n_data-1), (-1, n_data-1), TOTAL),
        # bordas
        ('LINEBELOW',    (0, 0), (-1, 0),         0.5, colors.HexColor('#495057')),
        ('LINEBELOW',    (0, 1), (-1, n_data-2),  0.3, LINHA),
        ('LINEABOVE',    (0, n_data-1), (-1, n_data-1), 0.8, colors.HexColor('#93b4f5')),
        # padding
        ('TOPPADDING',   (0, 0), (-1, -1),  4),
        ('BOTTOMPADDING',(0, 0), (-1, -1),  4),
        ('LEFTPADDING',  (0, 0), (-1, -1),  4),
        ('RIGHTPADDING', (0, 0), (-1, -1),  4),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    els.append(t)
    doc.build(els)

    label = f'propostas_{situacao or "todas"}'
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{label}.pdf"'
    return response


# ── kanban ────────────────────────────────────────────────────────────────────

@login_required
def proposta_kanban(request):
    from decimal import Decimal
    from django.db.models import F, Sum, ExpressionWrapper, DecimalField as DField

    todas = list(
        Proposta.objects
        .select_related('empreendimento', 'imobiliaria', 'corretor')
        .prefetch_related('participantes__pessoa', 'unidades__unidade__bloco')
    )

    totais = dict(
        SerieProposta.objects
        .filter(origem='proposta')
        .values('proposta_id')
        .annotate(total=Sum(ExpressionWrapper(
            F('valor') * F('quantidade'),
            output_field=DField(max_digits=16, decimal_places=2),
        )))
        .values_list('proposta_id', 'total')
    )

    from .models import WorkflowEtapa
    etapas = list(WorkflowEtapa.objects.order_by('ordem'))

    agrupadas = {e.slug: [] for e in etapas}
    for p in todas:
        p.kanban_valor = totais.get(p.pk, Decimal('0'))
        agrupadas.setdefault(p.situacao, []).append(p)

    colunas = []
    for e in etapas:
        grupo = agrupadas.get(e.slug, [])
        colunas.append({
            'slug':     e.slug,
            'label':    e.label,
            'cor':      e.cor,
            'propostas': grupo,
            'count':    len(grupo),
            'total':    sum(p.kanban_valor for p in grupo),
        })

    return render(request, 'propostas/proposta_kanban.html', {'colunas': colunas})


# ── criar ─────────────────────────────────────────────────────────────────────

@login_required
def proposta_create(request):
    if request.method == 'POST':
        p = request.POST
        try:
            proposta = Proposta(
                data=p['data'],
                imobiliaria=Pessoa.objects.get(pk=p['imobiliaria']),
                corretor=Pessoa.objects.get(pk=p['corretor']),
                empreendimento=Empreendimento.objects.get(pk=p['empreendimento']),
                tabela=TabelaVendas.objects.get(pk=p['tabela']),
                observacoes=p.get('observacoes', ''),
            )
            proposta.save()
            unidade = None
            unidade_pk = p.get('unidade')
            if unidade_pk:
                try:
                    unidade = Unidade.objects.get(pk=unidade_pk)
                    UnidadeProposta.objects.create(proposta=proposta, unidade=unidade)
                except Unidade.DoesNotExist:
                    pass
            _copiar_series_da_tabela(proposta, unidade=unidade)
            messages.success(request, f'Proposta {proposta.numero} criada.')
            return redirect('propostas:proposta_detail', numero=proposta.numero)
        except Exception as e:
            messages.error(request, f'Erro ao criar proposta: {e}')

    return render(request, 'propostas/proposta_form.html', {
        'imobiliarias':    Pessoa.objects.filter(is_imobiliaria=True, ativo=True).order_by('nome'),
        'corretores':      Pessoa.objects.filter(is_corretor=True, ativo=True).order_by('nome'),
        'empreendimentos': Empreendimento.objects.order_by('nome'),
    })


# ── detalhe ───────────────────────────────────────────────────────────────────

def _calcular_fluxo(series_proposta):
    """Retorna lista de parcelas ordenadas cronologicamente."""
    from datetime import date as date_type
    from dateutil.relativedelta import relativedelta

    parcelas = []
    for s in series_proposta:
        for i in range(s.quantidade):
            if s.primeiro_vencimento:
                vcto = s.primeiro_vencimento + relativedelta(months=i)
            else:
                vcto = None
            parcelas.append({
                'serie':         s.label,
                'indexador':     s.get_indexador_display(),
                'parcela':       i + 1,
                'total':         s.quantidade,
                'vencimento':    vcto,
                'valor':         s.valor,
            })

    parcelas.sort(key=lambda x: (x['vencimento'] is None, x['vencimento'] or date_type.min))
    for n, p in enumerate(parcelas, 1):
        p['num'] = n
    return parcelas


@login_required
def proposta_detail(request, numero):
    proposta = _get_proposta(numero)
    series_tabela   = proposta.series.filter(origem='tabela').order_by('ordem')
    series_proposta = proposta.series.filter(origem='proposta').order_by('ordem')
    fluxo           = _calcular_fluxo(list(series_proposta))

    return render(request, 'propostas/proposta_detail.html', {
        'proposta':         proposta,
        'series_tabela':    series_tabela,
        'series_proposta':  series_proposta,
        'fluxo':            fluxo,
        'situacao_choices': _etapas_choices(),
        'etapas_map':       _etapas_map(),
        'pessoas':          Pessoa.objects.filter(ativo=True).order_by('nome'),
        'unidades_disponiveis': (
            Unidade.objects
            .filter(
                bloco__empreendimento=proposta.empreendimento,
                unidade_principal__isnull=True,
            )
            .exclude(propostas__proposta=proposta)
            .select_related('bloco')
            .prefetch_related(
                Prefetch('vinculadas', queryset=Unidade.objects.order_by('ordem', 'numero'))
            )
            .order_by('bloco__nome', 'ordem', 'numero')
        ),
        'papel_choices':    ParticipanteProposta.PAPEL_CHOICES,
        'indexador_choices':SerieProposta.INDEXADOR_CHOICES,
        'tipo_choices':     SerieProposta.TIPO_CHOICES,
        'doc_tipo_choices': DocumentoProposta.TIPO_CHOICES,
    })


# ── editar campos básicos ─────────────────────────────────────────────────────

@login_required
def proposta_edit(request, numero):
    proposta = get_object_or_404(Proposta, numero=numero)
    if request.method == 'POST':
        p = request.POST
        proposta.situacao        = p.get('situacao', proposta.situacao)
        proposta.data            = p.get('data', proposta.data)
        proposta.numero_contrato = p.get('numero_contrato', '')
        proposta.observacoes     = p.get('observacoes', '')
        try:
            proposta.imobiliaria   = Pessoa.objects.get(pk=p['imobiliaria'])
            proposta.corretor      = Pessoa.objects.get(pk=p['corretor'])
            proposta.empreendimento= Empreendimento.objects.get(pk=p['empreendimento'])
            proposta.tabela        = TabelaVendas.objects.get(pk=p['tabela'])
            proposta.save()
            messages.success(request, 'Proposta atualizada.')
        except Exception as e:
            messages.error(request, f'Erro: {e}')
        return redirect('propostas:proposta_detail', numero=proposta.numero)

    return render(request, 'propostas/proposta_form.html', {
        'proposta':        proposta,
        'imobiliarias':    Pessoa.objects.filter(is_imobiliaria=True, ativo=True).order_by('nome'),
        'corretores':      Pessoa.objects.filter(is_corretor=True, ativo=True).order_by('nome'),
        'empreendimentos': Empreendimento.objects.order_by('nome'),
        'situacao_choices': _etapas_choices(),
    })


# ── excluir ───────────────────────────────────────────────────────────────────

@login_required
def proposta_delete(request, numero):
    proposta = get_object_or_404(Proposta, numero=numero)
    if request.method == 'POST':
        for doc in proposta.documentos.all():
            doc.arquivo.delete(save=False)
        proposta.delete()
        messages.success(request, f'Proposta {numero} excluída.')
        return redirect('propostas:proposta_list')
    return redirect('propostas:proposta_detail', numero=numero)


# ── unidades ──────────────────────────────────────────────────────────────────

@login_required
def unidade_add(request, numero):
    if request.method == 'POST':
        proposta = get_object_or_404(Proposta, numero=numero)
        unidade_pk = request.POST.get('unidade')
        if unidade_pk:
            was_empty = not proposta.unidades.exists()
            unidade = get_object_or_404(Unidade, pk=unidade_pk)
            _, created = UnidadeProposta.objects.get_or_create(proposta=proposta, unidade=unidade)
            # Adiciona automaticamente as unidades auxiliares vinculadas
            for aux in unidade.vinculadas.all():
                UnidadeProposta.objects.get_or_create(proposta=proposta, unidade=aux)
            if was_empty and created:
                sem_valores = not proposta.series.filter(origem='proposta').exclude(valor=0).exists()
                if sem_valores:
                    _copiar_series_da_tabela(proposta, unidade=unidade)
    return redirect('propostas:proposta_detail', numero=numero)


@login_required
def unidade_remove(request, pk):
    u = get_object_or_404(UnidadeProposta, pk=pk)
    numero = u.proposta.numero
    u.delete()
    return redirect('propostas:proposta_detail', numero=numero)


# ── participantes ─────────────────────────────────────────────────────────────

@login_required
def participante_add(request, numero):
    if request.method == 'POST':
        proposta   = get_object_or_404(Proposta, numero=numero)
        pessoa_pk  = request.POST.get('pessoa')
        papel      = request.POST.get('papel', 'proponente')
        if pessoa_pk:
            pessoa = get_object_or_404(Pessoa, pk=pessoa_pk)
            ParticipanteProposta.objects.get_or_create(proposta=proposta, pessoa=pessoa, papel=papel)
    return redirect('propostas:proposta_detail', numero=numero)


@login_required
def participante_remove(request, pk):
    p = get_object_or_404(ParticipanteProposta, pk=pk)
    numero = p.proposta.numero
    p.delete()
    return redirect('propostas:proposta_detail', numero=numero)


# ── fluxo PDF ────────────────────────────────────────────────────────────────

@login_required
def proposta_fluxo_pdf(request, numero):
    from io import BytesIO
    from decimal import Decimal
    from django.http import HttpResponse
    from django.utils import timezone
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER

    proposta        = _get_proposta(numero)
    series_proposta = proposta.series.filter(origem='proposta').order_by('ordem')
    fluxo           = _calcular_fluxo(list(series_proposta))

    def _brl(v):
        s = f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f'R$ {s}'

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )

    titulo_s  = ParagraphStyle('t',  fontName='Helvetica-Bold', fontSize=12, spaceAfter=2)
    sub_s     = ParagraphStyle('s',  fontName='Helvetica',      fontSize=8,  spaceAfter=8, textColor=colors.HexColor('#6c757d'))
    cell_s    = ParagraphStyle('c',  fontName='Helvetica',      fontSize=8,  leading=10)
    hdr_s     = ParagraphStyle('h',  fontName='Helvetica-Bold', fontSize=8,  leading=10, textColor=colors.white)
    num_s     = ParagraphStyle('n',  fontName='Helvetica',      fontSize=8,  leading=10, textColor=colors.HexColor('#6c757d'))
    val_s     = ParagraphStyle('v',  fontName='Helvetica-Bold', fontSize=8,  leading=10, alignment=TA_RIGHT)
    ctr_s     = ParagraphStyle('ct', fontName='Helvetica',      fontSize=8,  leading=10, alignment=TA_CENTER, textColor=colors.HexColor('#6c757d'))
    tot_s     = ParagraphStyle('to', fontName='Helvetica-Bold', fontSize=8,  leading=10)
    tot_val_s = ParagraphStyle('tv', fontName='Helvetica-Bold', fontSize=8,  leading=10, alignment=TA_RIGHT)

    proponentes = [pt.pessoa.nome for pt in proposta.participantes.all() if pt.papel == 'proponente']
    proponente_str = ', '.join(proponentes) if proponentes else '—'

    els = [
        Paragraph(f'Fluxo de Pagamentos — {proposta.numero}', titulo_s),
        Paragraph(
            f'{proposta.empreendimento}  ·  Proponente: {proponente_str}  ·  '
            f'Gerado em {timezone.localdate().strftime("%d/%m/%Y")}',
            sub_s
        ),
    ]

    headers = ['#', 'Vencimento', 'Série', 'Parcela', 'Valor', 'Indexador']
    rows = [[Paragraph(h, hdr_s) for h in headers]]

    total = Decimal('0')
    for p in fluxo:
        vcto_str = p['vencimento'].strftime('%d/%m/%Y') if p['vencimento'] else '—'
        idx = p['indexador'] if p['indexador'] != 'Nenhum' else '—'
        total += p['valor']
        rows.append([
            Paragraph(str(p['num']),              num_s),
            Paragraph(vcto_str,                   cell_s),
            Paragraph(p['serie'],                 cell_s),
            Paragraph(f"{p['parcela']}/{p['total']}", ctr_s),
            Paragraph(_brl(p['valor']),            val_s),
            Paragraph(idx,                         cell_s),
        ])

    n = len(rows)
    rows.append([
        Paragraph('', cell_s),
        Paragraph('', cell_s),
        Paragraph('', cell_s),
        Paragraph(f"{len(fluxo)} parcela{'s' if len(fluxo) != 1 else ''}", tot_s),
        Paragraph(_brl(total), tot_val_s),
        Paragraph('', cell_s),
    ])

    col_w = [10*mm, 25*mm, 60*mm, 22*mm, 33*mm, 27*mm]
    CINZA = colors.HexColor('#343a40')
    LINHA = colors.HexColor('#dee2e6')
    TOTAL = colors.HexColor('#e8f0fe')

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0),  (-1, 0),         CINZA),
        ('ROWBACKGROUNDS', (0, 1),  (-1, n - 1),      [colors.white, colors.HexColor('#f8f9fa')]),
        ('BACKGROUND',     (0, n),  (-1, n),           TOTAL),
        ('LINEBELOW',      (0, 0),  (-1, 0),           0.5,  colors.HexColor('#495057')),
        ('LINEBELOW',      (0, 1),  (-1, n - 1),       0.3,  LINHA),
        ('LINEABOVE',      (0, n),  (-1, n),            0.8,  colors.HexColor('#93b4f5')),
        ('TOPPADDING',     (0, 0),  (-1, -1),  4),
        ('BOTTOMPADDING',  (0, 0),  (-1, -1),  4),
        ('LEFTPADDING',    (0, 0),  (-1, -1),  4),
        ('RIGHTPADDING',   (0, 0),  (-1, -1),  4),
        ('VALIGN',         (0, 0),  (-1, -1), 'MIDDLE'),
    ]))

    els.append(t)

    # ── Quadro de séries ──────────────────────────────────────────────────────
    sec_s  = ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=9,
                            spaceBefore=14, spaceAfter=4, textColor=colors.HexColor('#1a1a2e'))
    els.append(Paragraph('Resumo das Séries Propostas', sec_s))

    s_hdr_s  = ParagraphStyle('sh',  fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.white)
    s_cell_s = ParagraphStyle('sc',  fontName='Helvetica',      fontSize=7.5, leading=10)
    s_val_s  = ParagraphStyle('sv',  fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=TA_RIGHT)
    s_ctr_s  = ParagraphStyle('sct', fontName='Helvetica',      fontSize=7.5, leading=10, alignment=TA_CENTER)
    s_tot_s  = ParagraphStyle('stt', fontName='Helvetica-Bold', fontSize=7.5, leading=10, alignment=TA_RIGHT)

    s_headers = ['Série', 'Tipo', 'Parcelas', '1º Vencimento', 'Valor/Parcela', 'Subtotal', 'Indexador']
    s_rows = [[Paragraph(h, s_hdr_s) for h in s_headers]]

    subtotal_geral = Decimal('0')
    for s in series_proposta:
        vcto_s = s.primeiro_vencimento.strftime('%d/%m/%Y') if s.primeiro_vencimento else '—'
        sub = s.valor * s.quantidade
        subtotal_geral += sub
        idx = s.get_indexador_display() if s.indexador != 'nenhum' else '—'
        s_rows.append([
            Paragraph(s.label,                  s_cell_s),
            Paragraph(s.get_tipo_display(),      s_cell_s),
            Paragraph(str(s.quantidade),         s_ctr_s),
            Paragraph(vcto_s,                    s_cell_s),
            Paragraph(_brl(s.valor),             s_val_s),
            Paragraph(_brl(sub),                 s_val_s),
            Paragraph(idx,                       s_cell_s),
        ])

    sn = len(s_rows)
    s_rows.append([
        Paragraph('', s_cell_s),
        Paragraph('', s_cell_s),
        Paragraph('', s_cell_s),
        Paragraph('', s_cell_s),
        Paragraph('Total', s_tot_s),
        Paragraph(_brl(subtotal_geral), s_tot_s),
        Paragraph('', s_cell_s),
    ])

    s_col_w = [55*mm, 20*mm, 18*mm, 26*mm, 28*mm, 28*mm, 22*mm]
    AZUL    = colors.HexColor('#1e3a5f')

    st = Table(s_rows, colWidths=s_col_w, repeatRows=1)
    st.setStyle(TableStyle([
        ('BACKGROUND',     (0, 0),   (-1, 0),          AZUL),
        ('ROWBACKGROUNDS', (0, 1),   (-1, sn - 1),     [colors.white, colors.HexColor('#f0f4ff')]),
        ('BACKGROUND',     (0, sn),  (-1, sn),          TOTAL),
        ('LINEBELOW',      (0, 0),   (-1, 0),            0.5,  colors.HexColor('#3a5f8a')),
        ('LINEBELOW',      (0, 1),   (-1, sn - 1),       0.3,  LINHA),
        ('LINEABOVE',      (0, sn),  (-1, sn),            0.8,  colors.HexColor('#93b4f5')),
        ('TOPPADDING',     (0, 0),   (-1, -1),  4),
        ('BOTTOMPADDING',  (0, 0),   (-1, -1),  4),
        ('LEFTPADDING',    (0, 0),   (-1, -1),  4),
        ('RIGHTPADDING',   (0, 0),   (-1, -1),  4),
        ('VALIGN',         (0, 0),   (-1, -1), 'MIDDLE'),
    ]))

    els.append(st)
    doc.build(els)

    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="fluxo_{numero}.pdf"'
    return response


# ── séries ────────────────────────────────────────────────────────────────────

@login_required
def serie_add(request, numero):
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        proposta = get_object_or_404(Proposta, numero=numero)
        p = request.POST
        try:
            valor = Decimal(str(p.get('valor', '0')).replace(',', '.'))
            SerieProposta.objects.create(
                proposta=proposta,
                origem='proposta',
                label=p.get('label', ''),
                tipo=p.get('tipo', 'fixa'),
                quantidade=int(p.get('quantidade', 1)),
                valor=valor,
                primeiro_vencimento=p.get('primeiro_vencimento') or None,
                indexador=p.get('indexador', 'nenhum'),
                ordem=proposta.series.filter(origem='proposta').count(),
            )
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Erro ao adicionar série: {e}')
    return redirect('propostas:proposta_detail', numero=numero)


@login_required
def serie_edit(request, pk):
    from decimal import Decimal, InvalidOperation
    serie = get_object_or_404(SerieProposta, pk=pk)
    if request.method == 'POST' and serie.origem == 'proposta':
        p = request.POST
        try:
            serie.label               = p.get('label', serie.label)
            serie.tipo                = p.get('tipo', serie.tipo)
            serie.quantidade          = int(p.get('quantidade', serie.quantidade))
            serie.valor               = Decimal(str(p.get('valor', '0')).replace(',', '.'))
            serie.primeiro_vencimento = p.get('primeiro_vencimento') or None
            serie.indexador           = p.get('indexador', serie.indexador)
            serie.save()
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Erro: {e}')
    return redirect('propostas:proposta_detail', numero=serie.proposta.numero)


@login_required
def serie_remove(request, pk):
    serie = get_object_or_404(SerieProposta, pk=pk, origem='proposta')
    numero = serie.proposta.numero
    serie.delete()
    return redirect('propostas:proposta_detail', numero=numero)


@login_required
def series_copiar_tabela(request, numero):
    """Recopia as séries da TabelaVendas, substituindo tabela e proposta."""
    proposta = get_object_or_404(Proposta, numero=numero)
    _copiar_series_da_tabela(proposta)
    messages.success(request, 'Séries atualizadas a partir da tabela.')
    return redirect('propostas:proposta_detail', numero=numero)


# ── documentos ────────────────────────────────────────────────────────────────

@login_required
def documento_upload(request, numero):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        proposta = get_object_or_404(Proposta, numero=numero)
        participante_pk = request.POST.get('participante') or None
        participante = None
        if participante_pk:
            participante = get_object_or_404(ParticipanteProposta, pk=participante_pk, proposta=proposta)
        DocumentoProposta.objects.create(
            proposta=proposta,
            participante=participante,
            tipo=request.POST.get('tipo', 'outro'),
            arquivo=request.FILES['arquivo'],
            descricao=request.POST.get('descricao', ''),
        )
        messages.success(request, 'Documento anexado.')
    return redirect('propostas:proposta_detail', numero=numero)


@login_required
def documento_remove(request, pk):
    doc = get_object_or_404(DocumentoProposta, pk=pk)
    numero = doc.proposta.numero
    doc.arquivo.delete(save=False)
    doc.delete()
    return redirect('propostas:proposta_detail', numero=numero)


# ── workflow ──────────────────────────────────────────────────────────────────

def _default_drawflow():
    positions = {
        'rascunho':            (60,  220),
        'enviada':             (300, 220),
        'em_analise':          (540, 220),
        'aprovada':            (540,  80),
        'reprovada':           (540, 360),
        'contrato_elaborado':  (780,  80),
        'contratada':          (1020, 80),
    }
    nodes = {}
    for i, (val, label) in enumerate(Proposta.SITUACAO_CHOICES):
        nid = i + 1
        x, y = positions.get(val, (100 + i * 200, 220))
        nodes[str(nid)] = {
            'id': nid,
            'name': val,
            'data': {},
            'class': val,
            'html': f'<div class="wf-node-header">{label}</div>',
            'typenode': False,
            'inputs':  {'input_1':  {'connections': []}},
            'outputs': {'output_1': {'connections': []}},
            'pos_x': x,
            'pos_y': y,
        }
    return {'drawflow': {'Home': {'data': nodes}}}


@login_required
def proposta_workflow(request):
    data = _build_drawflow()
    return render(request, 'propostas/proposta_workflow.html', {
        'drawflow_data': json.dumps(data),
    })


@login_required
def workflow_salvar(request):
    if request.method == 'POST':
        from .models import WorkflowConfig
        try:
            data = json.loads(request.body)
            _sync_from_drawflow(data)
            config, _ = WorkflowConfig.objects.get_or_create(pk=1)
            config.drawflow_json = data
            config.save()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'POST only'}, status=405)


@login_required
def etapa_criar(request):
    if request.method == 'POST':
        import re
        from .models import WorkflowEtapa
        data = json.loads(request.body)
        label = data.get('label', '').strip()
        cor   = data.get('cor', '#6c757d')
        if not label:
            return JsonResponse({'error': 'Nome obrigatório'}, status=400)
        slug = re.sub(r'[^a-z0-9]+', '_', label.lower()).strip('_') or 'etapa'
        base, i = slug, 1
        while WorkflowEtapa.objects.filter(slug=slug).exists():
            slug = f'{base}_{i}'; i += 1
        etapa = WorkflowEtapa.objects.create(
            slug=slug, label=label, cor=cor,
            ordem=WorkflowEtapa.objects.count(),
            pos_x=data.get('pos_x', 200), pos_y=data.get('pos_y', 200),
        )
        return JsonResponse({
            'slug':  etapa.slug,
            'label': etapa.label,
            'cor':   etapa.cor,
            'html':  f'<div class="wf-node-header" style="background:{etapa.cor}">{etapa.label}</div>',
        })
    return JsonResponse({'error': 'POST only'}, status=405)


@login_required
def etapa_excluir(request, slug):
    if request.method == 'POST':
        from .models import WorkflowEtapa
        etapa = get_object_or_404(WorkflowEtapa, slug=slug)
        count = Proposta.objects.filter(situacao=slug).count()
        if count:
            return JsonResponse({'error': f'Existem {count} proposta(s) com essa situação. Altere-as primeiro.'}, status=400)
        etapa.delete()
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'POST only'}, status=405)


# ── AJAX helpers ──────────────────────────────────────────────────────────────

@login_required
def tabela_unidades_json(request, tabela_pk):
    from apps.incorporadora.models import ItemTabelaVendas
    itens = (ItemTabelaVendas.objects
             .filter(tabela_id=tabela_pk)
             .select_related('unidade__bloco')
             .order_by('unidade__bloco__nome', 'unidade__numero'))
    data = [{'pk': it.unidade_id, 'label': f"{it.unidade.bloco.nome} — {it.unidade.numero}"}
            for it in itens]
    return JsonResponse(data, safe=False)
