from django.shortcuts import render
from django.db.models import Sum, Count, Q

from .models import ImportacaoMaxFlora, UnidadeMaxFlora


def _fmt_brl(v):
    if v is None:
        return ''
    return f'R$ {v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def tabela_vendas(request):
    importacao = ImportacaoMaxFlora.objects.first()
    unidades = []
    stats = {}

    if importacao:
        qs = UnidadeMaxFlora.objects.filter(importacao=importacao)
        unidades = list(qs)

        total = qs.count()
        locadas = qs.filter(situacao='LOCADO').count()
        disponiveis = total - locadas
        area_total = qs.aggregate(s=Sum('area_total'))['s'] or 0
        val_total = qs.exclude(euc='Estac.').aggregate(s=Sum('valor_vendas'))['s'] or 0

        stats = {
            'total': total,
            'locadas': locadas,
            'disponiveis': disponiveis,
            'pct_locado': round(locadas / total * 100) if total else 0,
            'area_total': f'{area_total:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.'),
            'valor_total': _fmt_brl(val_total),
            'importado_em': importacao.importado_em,
            'arquivo': importacao.arquivo,
        }

    return render(request, 'maxflora/tabela.html', {
        'unidades': unidades,
        'stats': stats,
        'importacao': importacao,
    })
