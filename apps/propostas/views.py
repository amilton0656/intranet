import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
    from .models import WorkflowEtapa, WorkflowTransicao
    nodes = data.get('drawflow', {}).get('Home', {}).get('data', {})
    for node in nodes.values():
        slug = node.get('name', '')
        if slug:
            WorkflowEtapa.objects.filter(slug=slug).update(
                pos_x=node.get('pos_x', 100),
                pos_y=node.get('pos_y', 100),
            )
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
            'val':      e.slug,
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

@login_required
def proposta_detail(request, numero):
    proposta = _get_proposta(numero)
    series_tabela   = proposta.series.filter(origem='tabela').order_by('ordem')
    series_proposta = proposta.series.filter(origem='proposta').order_by('ordem')

    return render(request, 'propostas/proposta_detail.html', {
        'proposta':         proposta,
        'series_tabela':    series_tabela,
        'series_proposta':  series_proposta,
        'situacao_choices': _etapas_choices(),
        'etapas_map':       _etapas_map(),
        'pessoas':          Pessoa.objects.filter(ativo=True).order_by('nome'),
        'unidades_disponiveis': (
            Unidade.objects
            .filter(bloco__empreendimento=proposta.empreendimento)
            .exclude(propostas__proposta=proposta)
            .select_related('bloco')
            .order_by('bloco__nome', 'numero')
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
