"""Análise anual em 3 estágios: resumo por empresa -> fluxo mensal da
empresa -> detalhe do mês. Usa Recebimento (dinheiro que entrou) para
Incorporação/Locação/Recebimentos e Contrato (valor total vendido) para
Vendas."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.shortcuts import render

from .models import Contrato, Recebimento
from .views import _fmt_mes


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


def resumo(request):
    """Estágio 1 — Faturamentos últimos 12 meses, por empresa: Vendas x Recebimentos."""
    empresas = _empresas_disponiveis()
    codigos = [codigo for codigo, _ in empresas]

    hoje = date.today()
    mes_atual = date(hoje.year, hoje.month, 1)
    meses = [_mes_menos(mes_atual, i) for i in range(11, -1, -1)]

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

    return render(request, 'faturamento/anual_resumo.html', {
        'empresas': empresas,
        'linhas': linhas,
        'rodape': rodape,
        'total_geral_vendas': total_geral_vendas,
        'total_geral_recebimentos': total_geral_recebimentos,
    })


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

    recebimentos = list(recebimentos_qs.order_by('-valor_liquido'))
    incorporacao = [r for r in recebimentos if r.categoria == Recebimento.INCORPORACAO]
    locacao = [r for r in recebimentos if r.categoria == Recebimento.LOCACAO]

    vendas = sorted(
        (c for c in contratos_qs if c.mes_venda_efetivo and inicio <= c.mes_venda_efetivo < fim),
        key=lambda c: -c.valor_total,
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
