"""Parsers dos CSVs de faturamento (Sienge): baixas (recebido) e contas a
receber (pendente), e o cálculo de `Contrato` a partir dos dois."""

import csv
import io
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction

from .models import (
    Contrato, ImportacaoAReceber, ImportacaoFaturamento, ParcelaPendente, Recebimento,
)


def _to_float(v):
    v = (v or '').strip()
    if not v:
        return 0.0
    return float(v.replace('.', '').replace(',', '.')) if ',' in v else float(v)


def _to_date(v):
    v = (v or '').strip()
    return datetime.strptime(v, '%d/%m/%Y').date() if v else None


def _categoria(codigo_plano_financeiro):
    codigo = (codigo_plano_financeiro or '').strip()
    if codigo.startswith('101'):
        return Recebimento.INCORPORACAO
    if codigo.startswith('103'):
        return Recebimento.LOCACAO
    return Recebimento.OUTROS


# ── Recebido (baixas) ───────────────────────────────────────────────────────

def parse_csv(fileobj):
    """Lê bytes/file-like do CSV de baixas e retorna lista de dicts prontos para salvar."""
    text = fileobj.read()
    if isinstance(text, bytes):
        text = text.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text), delimiter=';')

    linhas = []
    for row in reader:
        data_baixa = _to_date(row.get('DataDaBaixa'))
        if not data_baixa:
            continue
        linhas.append({
            'codigo_empresa': (row.get('CodigoDaEmpresa') or '').strip(),
            'nome_empresa': (row.get('NomeDaEmpresa') or '').strip(),
            'codigo_centro_custo': (row.get('CodigoDoCentroDeCusto') or '').strip(),
            'nome_centro_custo': (row.get('NomeDoCentroDeCusto') or '').strip(),
            'codigo_cliente': (row.get('CodigoDoCliente') or '').strip(),
            'nome_cliente': (row.get('NomeDoCliente') or '').strip(),
            'numero_titulo': (row.get('NumeroDoTitulo') or '').strip(),
            'numero_parcela': (row.get('NumeroDaParcela') or '').strip(),
            'numero_unidade': (row.get('NumeroDaUnidade') or '').strip(),
            'codigo_plano_financeiro': (row.get('CodigoDoPlanoFinanceiro') or '').strip(),
            'nome_plano_financeiro': (row.get('NomeDoPlanoFinanceiro') or '').strip(),
            'categoria': _categoria(row.get('CodigoDoPlanoFinanceiro')),
            'data_baixa': data_baixa,
            'data_emissao': _to_date(row.get('DataDeEmissao')),
            'valor_baixa': _to_float(row.get('ValorDaBaixa')),
            'valor_liquido': _to_float(row.get('ValorLiquido')),
        })
    return linhas


def salvar_importacao(nome_arquivo, linhas):
    """Substitui completamente os recebimentos anteriores pelos da nova importação."""
    with transaction.atomic():
        imp = ImportacaoFaturamento.objects.create(
            arquivo=nome_arquivo,
            total_linhas=len(linhas),
        )
        Recebimento.objects.bulk_create(
            [Recebimento(importacao=imp, **linha) for linha in linhas]
        )
        ImportacaoFaturamento.objects.exclude(pk=imp.pk).delete()
    return imp


# ── A receber (pendente) ────────────────────────────────────────────────────

def parse_areceber_csv(fileobj):
    """Lê o CSV de contas a receber e retorna lista de dicts prontos para salvar.

    Descarta linhas com chave duplicada (mesmo título/parcela/tipo/vencimento
    repetido) — efeito colateral conhecido do relatório do Sienge que faria o
    saldo pendente ser contado em dobro (ver contrato 178/LITOSUL).
    """
    text = fileobj.read()
    if isinstance(text, bytes):
        text = text.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text), delimiter=';')

    linhas = []
    vistos = set()
    for row in reader:
        vencimento = _to_date(row.get('dtVencto'))
        if not vencimento:
            continue
        chave = (
            (row.get('nuTitulo') or '').strip(),
            (row.get('nuParcelaApresentacao') or '').strip(),
            (row.get('cdTipoCondicao') or '').strip(),
            (row.get('dtVencto') or '').strip(),
        )
        if chave in vistos:
            continue
        vistos.add(chave)
        linhas.append({
            'codigo_empresa': (row.get('cdEmpresa') or '').strip(),
            'nome_empresa': (row.get('nmEmpresa') or '').strip(),
            'nome_cliente': (row.get('nmCliente') or '').strip(),
            'numero_documento': (row.get('nuDocumento') or '').strip(),
            'numero_titulo': (row.get('nuTitulo') or '').strip(),
            'numero_parcela': (row.get('nuParcelaApresentacao') or '').strip(),
            'tipo_condicao': (row.get('cdTipoCondicao') or '').strip(),
            'numero_unidade': (row.get('nuUnidadePrincipal') or '').strip(),
            'vencimento': vencimento,
            'valor_original': _to_float(row.get('vlOriginal')),
            'valor_saldo_atual': _to_float(row.get('vlSaldoAtual')),
        })
    return linhas


def salvar_importacao_areceber(nome_arquivo, linhas):
    """Substitui completamente as parcelas pendentes anteriores pelas da nova importação."""
    with transaction.atomic():
        imp = ImportacaoAReceber.objects.create(
            arquivo=nome_arquivo,
            total_linhas=len(linhas),
        )
        ParcelaPendente.objects.bulk_create(
            [ParcelaPendente(importacao=imp, **linha) for linha in linhas]
        )
        ImportacaoAReceber.objects.exclude(pk=imp.pk).delete()
    return imp


# ── Contrato (agregação título a título) ───────────────────────────────────

# Correções manuais conhecidas, aplicadas só na primeira vez que o contrato é
# criado (depois disso, `mes_venda_manual` já fica salvo e sobrevive a
# reimportações — editável no Admin se precisar mudar de novo).
SEED_OVERRIDES = {
    # LITOSUL (permuta): tem chave duplicada no a_receber (bug de reconcile,
    # ver project_permutas_bugs) e a DataDeEmissao (02/07/2026) não reflete
    # quando o negócio foi realmente fechado — usuário pediu 08/2026.
    ('1', '178'): date(2026, 8, 1),
    # Permuta de 2019 pra unidade 308, nunca paga; a mesma unidade foi
    # revendida em 2026 (título 205). Registro antigo/provavelmente superado
    # — jogado pra antes do início real dos dados (01/2013) pra não poluir os
    # números atuais, a pedido do usuário.
    ('1', '88'): date(2012, 12, 1),
}


def recalcular_contratos():
    """Recalcula a tabela Contrato a partir de Recebimento + ParcelaPendente.

    Um "contrato" é o agrupamento de tudo que tem o mesmo NumeroDoTitulo (pra
    empresa). valor_total = já recebido (Recebimento) + ainda pendente
    (ParcelaPendente). mes_venda = mês da DataDeEmissao (se o título já tem
    alguma baixa) ou, na falta dela, o mês do vencimento mais próximo (título
    novo, ainda sem nenhuma baixa registrada).
    """
    recebido = defaultdict(lambda: {
        'nome_empresa': '', 'nome_cliente': '', 'categoria': None,
        'valor_recebido': Decimal('0'), 'data_emissao_min': None,
        'codigo_centro_custo': '', 'nome_centro_custo': '',
    })
    for r in Recebimento.objects.exclude(numero_titulo='').values(
        'codigo_empresa', 'nome_empresa', 'numero_titulo', 'nome_cliente',
        'categoria', 'valor_liquido', 'data_emissao',
        'codigo_centro_custo', 'nome_centro_custo',
    ):
        key = (r['codigo_empresa'], r['numero_titulo'])
        d = recebido[key]
        d['nome_empresa'] = r['nome_empresa']
        d['nome_cliente'] = r['nome_cliente']
        if r['categoria'] and r['categoria'] != Recebimento.OUTROS:
            d['categoria'] = r['categoria']
        if r['codigo_centro_custo']:
            d['codigo_centro_custo'] = r['codigo_centro_custo']
            d['nome_centro_custo'] = r['nome_centro_custo']
        d['valor_recebido'] += r['valor_liquido']
        if r['data_emissao'] and (not d['data_emissao_min'] or r['data_emissao'] < d['data_emissao_min']):
            d['data_emissao_min'] = r['data_emissao']

    pendente = defaultdict(lambda: {
        'nome_empresa': '', 'nome_cliente': '',
        'valor_pendente': Decimal('0'), 'vencimento_min': None,
    })
    for r in ParcelaPendente.objects.values(
        'codigo_empresa', 'nome_empresa', 'numero_titulo', 'nome_cliente',
        'valor_original', 'vencimento',
    ):
        key = (r['codigo_empresa'], r['numero_titulo'])
        d = pendente[key]
        d['nome_empresa'] = r['nome_empresa']
        d['nome_cliente'] = r['nome_cliente']
        d['valor_pendente'] += r['valor_original']
        if r['vencimento'] and (not d['vencimento_min'] or r['vencimento'] < d['vencimento_min']):
            d['vencimento_min'] = r['vencimento']

    todas_chaves = set(recebido) | set(pendente)
    pks_atuais = set()

    for codigo_empresa, numero_titulo in todas_chaves:
        key = (codigo_empresa, numero_titulo)
        rec = recebido.get(key)
        pend = pendente.get(key)

        nome_empresa = (rec and rec['nome_empresa']) or (pend and pend['nome_empresa']) or ''
        nome_cliente = (rec and rec['nome_cliente']) or (pend and pend['nome_cliente']) or ''
        # sem nenhuma baixa ainda pra saber o plano financeiro: assume venda
        # (é o padrão observado pra contratos novos sem baixa — locação não
        # costuma aparecer como título zerado).
        categoria = (rec and rec['categoria']) or Recebimento.INCORPORACAO
        codigo_centro_custo = (rec and rec['codigo_centro_custo']) or ''
        nome_centro_custo = (rec and rec['nome_centro_custo']) or ''
        valor_recebido = rec['valor_recebido'] if rec else Decimal('0')
        valor_pendente = pend['valor_pendente'] if pend else Decimal('0')

        mes_venda = None
        if rec and rec['data_emissao_min']:
            mes_venda = rec['data_emissao_min'].replace(day=1)
        elif pend and pend['vencimento_min']:
            mes_venda = pend['vencimento_min'].replace(day=1)

        contrato, created = Contrato.objects.update_or_create(
            codigo_empresa=codigo_empresa, numero_titulo=numero_titulo,
            defaults=dict(
                nome_empresa=nome_empresa,
                nome_cliente=nome_cliente,
                categoria=categoria,
                codigo_centro_custo=codigo_centro_custo,
                nome_centro_custo=nome_centro_custo,
                valor_recebido=valor_recebido,
                valor_pendente=valor_pendente,
                valor_total=valor_recebido + valor_pendente,
                mes_venda=mes_venda,
            ),
        )
        if created:
            override = SEED_OVERRIDES.get(key)
            if override:
                contrato.mes_venda_manual = override
                contrato.save(update_fields=['mes_venda_manual'])
        pks_atuais.add(contrato.pk)

    Contrato.objects.exclude(pk__in=pks_atuais).delete()
