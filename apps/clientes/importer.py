"""Parsers dos CSVs do Sienge: clientes.csv, contratos.csv (vendas) e
locações.csv. Upsert por chave natural (código do cliente / número do
contrato) — nunca "substitui tudo", porque um contrato pode ser corrigido
(valor, situação) num arquivo mais novo sem sumir do relatório."""

import csv
import io
from datetime import datetime

from django.db import transaction

from .models import Cliente, ContratoLocacao, ContratoVenda, ImportLog


def _to_float(v):
    v = (v or '').strip().replace('R$', '').replace('\xa0', '').strip()
    if not v:
        return 0.0
    return float(v.replace('.', '').replace(',', '.')) if ',' in v else float(v)


def _to_date(v):
    v = (v or '').strip()
    return datetime.strptime(v, '%d/%m/%Y').date() if v else None


def _open_csv(file_obj):
    raw = file_obj.read()
    if isinstance(raw, bytes):
        text = raw.decode('utf-8-sig')
    else:
        text = raw
    return io.StringIO(text)


def _tipo_pessoa(v):
    v = (v or '').strip().lower()
    if v.startswith('f'):
        return 'fisica'
    if v.startswith('j'):
        return 'juridica'
    return ''


@transaction.atomic
def importar_clientes(file_obj, nome):
    reader = csv.DictReader(_open_csv(file_obj), delimiter=';')
    n = 0
    for row in reader:
        codigo = (row.get('Código') or '').strip()
        if not codigo:
            continue
        Cliente.objects.update_or_create(
            codigo=codigo,
            defaults=dict(
                nome=(row.get('Nome') or '').strip(),
                tipo_pessoa=_tipo_pessoa(row.get('Tipo pessoa')),
                cpf_cnpj=(row.get('CNPJ/CPF') or '').strip(),
                data_nascimento=_to_date(row.get('Data de nascimento')),
                telefone=(row.get('Telefone principal') or '').strip(),
                email=(row.get('E-mail') or '').strip(),
                tipo_cliente=(row.get('Descrição tipo cliente') or '').strip(),
                situacao=(row.get('Situação') or '').strip(),
                cidade=(row.get('Município') or '').strip(),
                uf=(row.get('UF') or '').strip(),
            ),
        )
        n += 1
    if not n:
        raise ValueError('Nenhum cliente válido encontrado no arquivo.')
    ImportLog.objects.create(tipo='clientes', total_registros=n, nome_arquivo=nome)
    return n


@transaction.atomic
def importar_contratos_venda(file_obj, nome):
    reader = csv.DictReader(_open_csv(file_obj), delimiter=';')
    n = 0
    for row in reader:
        numero = (row.get('Contrato') or '').strip()
        codigo_cliente = (row.get('Cód.Cliente') or '').strip()
        if not numero or not codigo_cliente:
            continue
        cliente, _ = Cliente.objects.get_or_create(
            codigo=codigo_cliente,
            defaults={'nome': (row.get('Cliente') or '').strip()},
        )
        ContratoVenda.objects.update_or_create(
            numero_contrato=numero,
            defaults=dict(
                cliente=cliente,
                nome_empresa=(row.get('Empresa') or '').strip(),
                nome_empreendimento=(row.get('Empreendimento') or '').strip(),
                unidade=(row.get('Unidade') or '').strip(),
                data_contrato=_to_date(row.get('Data Contrato')),
                valor_total=_to_float(row.get('Valor Total')),
                tipo_venda=(row.get('Tipo Venda') or '').strip(),
                situacao=(row.get('Situação') or '').strip(),
                corretor=(row.get('Corretor') or '').strip(),
                data_distrato=_to_date(row.get('Data Distrato')),
            ),
        )
        n += 1
    if not n:
        raise ValueError('Nenhum contrato de venda válido encontrado no arquivo.')
    ImportLog.objects.create(tipo='vendas', total_registros=n, nome_arquivo=nome)
    return n


@transaction.atomic
def importar_contratos_locacao(file_obj, nome):
    reader = csv.DictReader(_open_csv(file_obj), delimiter=';')
    n = 0
    for row in reader:
        numero = (row.get('Contrato') or '').strip()
        codigo_cliente = (row.get('Cód. Cliente') or '').strip()
        if not numero or not codigo_cliente:
            continue
        cliente, _ = Cliente.objects.get_or_create(
            codigo=codigo_cliente,
            defaults={'nome': (row.get('Cliente') or '').strip()},
        )
        tempo_raw = (row.get('Tempo locação') or '').strip()
        ContratoLocacao.objects.update_or_create(
            numero_contrato=numero,
            defaults=dict(
                cliente=cliente,
                nome_empresa=(row.get('Empresa') or '').strip(),
                nome_empreendimento=(row.get('Empreendimento') or '').strip(),
                unidade=(row.get('Unidade') or '').strip(),
                data_contrato=_to_date(row.get('Data do contrato')),
                valor_contrato=_to_float(row.get('Valor do contrato')),
                valor_parcela=_to_float(row.get('Valor parcela')),
                tempo_locacao=int(tempo_raw) if tempo_raw.isdigit() else None,
                situacao=(row.get('Situação contrato') or '').strip(),
                data_cancelamento=_to_date(row.get('Data cancelamento')),
            ),
        )
        n += 1
    if not n:
        raise ValueError('Nenhum contrato de locação válido encontrado no arquivo.')
    ImportLog.objects.create(tipo='locacoes', total_registros=n, nome_arquivo=nome)
    return n
