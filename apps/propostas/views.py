from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse

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
        'situacao_choices': Proposta.SITUACAO_CHOICES,
    })


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
        'situacao_choices': Proposta.SITUACAO_CHOICES,
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
        'situacao_choices':Proposta.SITUACAO_CHOICES,
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
