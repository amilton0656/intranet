"""Parser do CSV de faturamento (relatório de baixas de recebimento do Sienge)."""

import csv
import io
from datetime import datetime

from django.db import transaction

from .models import ImportacaoFaturamento, Recebimento


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


def parse_csv(fileobj):
    """Lê bytes/file-like do CSV e retorna lista de dicts prontos para salvar."""
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
