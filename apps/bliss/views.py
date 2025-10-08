import unicodedata
import os
import datetime
import json
import time
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Bliss
from .forms import BlissForm
from django.http import HttpResponse, JsonResponse
from openpyxl import load_workbook
from django.db.models import Count, Sum
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db.models import F
from django.db.models import Count, Sum, F, FloatField, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal, DivisionByZero, InvalidOperation
from django.contrib import messages
from django.db import models

import csv
import io
from django.db import transaction
from io import BytesIO
from django.core.mail import EmailMessage
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.views.decorators.csrf import csrf_exempt

# WEBHOOK_PASSWORD = getattr(settings, 'BLISS_RESUMO_WEBHOOK_PASSWORD', '12345')


WEBHOOK_PASSWORD = os.getenv("BLISS_RESUMO_WEBHOOK_PASSWORD", "12345")
# @login_required
# def tab_bliss(request):
#     return render(request, "bliss/tab_bliss.html")

# @login_required
def bliss_unidades(request):
    registros = Bliss.objects.all()
    return render(request, 'bliss/bliss_unidades.html', {'registros': registros})

# Criar
def bliss_create(request):
    if request.method == 'POST':
        form = BlissForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('bliss_unidades')
    else:
        form = BlissForm()
    return render(request, 'bliss/bliss_form.html', {'form': form})

# Editar
def bliss_update(request, pk):
    registro = get_object_or_404(Bliss, pk=pk)
    form = BlissForm(request.POST or None, instance=registro)
    if form.is_valid():
        form.save()
        return redirect('bliss_unidades')
    return render(request, 'bliss/bliss_form.html', {'form': form})

# Excluir
def bliss_delete(request, pk):
    registro = get_object_or_404(Bliss, pk=pk)
    if request.method == 'POST':
        registro.delete()
        return redirect('bliss_unidades')
    return render(request, 'bliss/bliss_delete_confirm.html', {'registro': registro})

# RelatÃ³rio HTML
def bliss_unidades_full(request):
    sort = request.GET.get('sort', 'bloco')
    direction = request.GET.get('dir', 'asc')  # 'asc' ou 'desc'

    allowed = {
        'bloco', 'unidade', 'area_privativa', 'garagem', 'deposito',
        'area_total', 'tipologia', 'situacao', 'valor_tabela',
        'data_venda', 'valor_venda', 'cliente', 'email', 'perc_permuta'
    }
    if sort not in allowed:
        sort = 'bloco'
    if direction not in ('asc', 'desc'):
        direction = 'asc'

    def with_dir(field: str) -> str:
        return field if direction == 'asc' else f'-{field}'

    # monta a ordenaÃ§Ã£o
    order_by = []
    if sort == 'bloco':
        # 1Âº por bloco, 2Âº por unidade (mesma direÃ§Ã£o escolhida)
        order_by.append(with_dir('bloco'))
        order_by.append(with_dir('unidade'))
    else:
        order_by.append(with_dir(sort))

    registros = Bliss.objects.all().order_by(*order_by)

    context = {
        'registros': registros,
        'sort': sort,
        'dir': direction,
        'invert_dir': 'desc' if direction == 'asc' else 'asc',
    }
    return render(request, 'bliss/bliss_unidades_full.html', context)

# RelatÃ³rio PDF
def bliss_unidades_full_pdf(request):
    registros = Bliss.objects.all()
    template = get_template('bliss/bliss_unidades_full_pdf.html')
    html = template.render({'registros': registros})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio.pdf"'
    pisa_status = pisa.CreatePDF(html, dest=response)
    return response

# Resumo de SituaÃ§Ãµes
def bliss_summary(request):
    registros = Bliss.objects.all()

    resumo_dict = {}
    total_valor_tabela = Decimal('0')
    total_valor_venda = Decimal('0')
    total_unidades = 0

    for reg in registros:
        # valores brutos
        valor_tabela = reg.valor_tabela
        valor_venda = reg.valor_venda
        unidade = reg.unidade.lower()
        situacao = reg.situacao

        # Caso normal (nÃ£o Ã© loja)
        if unidade != 'loja':
            if situacao not in resumo_dict:
                resumo_dict[situacao] = {
                    'situacao': situacao,
                    'total_valor_tabela': Decimal('0'),
                    'total_valor_venda': Decimal('0'),
                    'total_unidades': 0,
                }

            resumo_dict[situacao]['total_valor_tabela'] += valor_tabela
            resumo_dict[situacao]['total_valor_venda'] += valor_venda
            resumo_dict[situacao]['total_unidades'] += 1

            total_valor_tabela += valor_tabela
            total_valor_venda += valor_venda
            total_unidades += 1

        # Caso especial: unidade == 'Loja'
        else:
            valor_permuta_tabela = valor_tabela * Decimal('0.12826')
            valor_permuta_venda = valor_venda * Decimal('0.12826')

            valor_restante_tabela = valor_tabela * Decimal('0.87174')
            valor_restante_venda = valor_venda * Decimal('0.87174')

            # Grupo "Permuta"
            if 'Permuta' not in resumo_dict:
                resumo_dict['Permuta'] = {
                    'situacao': 'Permuta',
                    'total_valor_tabela': Decimal('0'),
                    'total_valor_venda': Decimal('0'),
                    'total_unidades': 0,
                }

            resumo_dict['Permuta']['total_valor_tabela'] += valor_permuta_tabela
            resumo_dict['Permuta']['total_valor_venda'] += valor_permuta_venda
            resumo_dict['Permuta']['total_unidades'] += 1

            # Grupo restante â€” se situaÃ§Ã£o == Permuta, o restante vai para "DisponÃ­vel"
            grupo_restante = 'DisponÃ­vel' if situacao.lower() == 'permuta' else situacao

            if grupo_restante not in resumo_dict:
                resumo_dict[grupo_restante] = {
                    'situacao': grupo_restante,
                    'total_valor_tabela': Decimal('0'),
                    'total_valor_venda': Decimal('0'),
                    'total_unidades': 0,
                }

            resumo_dict[grupo_restante]['total_valor_tabela'] += valor_restante_tabela
            resumo_dict[grupo_restante]['total_valor_venda'] += valor_restante_venda
            resumo_dict[grupo_restante]['total_unidades'] += 1

            # Totais gerais
            total_valor_tabela += valor_tabela
            total_valor_venda += valor_venda
            total_unidades += 1

    # Percentuais
    resumo = []
    for item in resumo_dict.values():
        item['pct_valor_tabela'] = (item['total_valor_tabela'] / total_valor_tabela * 100) if total_valor_tabela else 0
        item['pct_valor_venda'] = (item['total_valor_venda'] / total_valor_venda * 100) if total_valor_venda else 0
        item['pct_unidades'] = (item['total_unidades'] / total_unidades * 100) if total_unidades else 0
        resumo.append(item)

    # Resumo das lojas
   # Lojas
    lojas = registros.filter(unidade__iexact='loja')
    qtd_lojas = lojas.count()
    m2_lojas = (lojas.aggregate(area=models.Sum('area_privativa'))['area'] or Decimal('0')) * Decimal('0.87174')

    venda_lojas = Decimal('0')

    for loja in lojas:
        fator = Decimal('0.12826') if loja.situacao.lower() == 'permuta' else Decimal('0.87174')
        venda_lojas += loja.valor_tabela * fator

    valor_m2_lojas = venda_lojas / m2_lojas if m2_lojas else Decimal('0')

    # Tipos (exceto loja)
    tipos = registros.filter(situacao__iexact='disponÃ­vel').exclude(unidade__iexact='loja')
    qtd_tipos = tipos.count()
    m2_tipos = tipos.aggregate(area=models.Sum('area_privativa'))['area'] or Decimal('0')
    venda_tipos = tipos.aggregate(total=models.Sum('valor_tabela'))['total'] or Decimal('0')
    valor_m2_tipos = venda_tipos / m2_tipos if m2_tipos else Decimal('0')
    preco_medio_tipo = venda_tipos / qtd_tipos if qtd_tipos else Decimal('0')

    # Totais
    qtd_total = qtd_lojas + qtd_tipos
    m2_total = m2_lojas + m2_tipos
    venda_total = venda_lojas + venda_tipos
    valor_m2_total = venda_total / m2_total if m2_total else Decimal('0')

    resumo_lojas = [
        {
            'preco_medio_tipo': None,
            'quantidade': qtd_lojas,
            'tipo': 'Loja',
            'm2': m2_lojas,
            'valor_venda': venda_lojas,
            'valor_m2': valor_m2_lojas
        },
        {
            'preco_medio_tipo': preco_medio_tipo,
            'quantidade': qtd_tipos,
            'tipo': 'Tipos',
            'm2': m2_tipos,
            'valor_venda': venda_tipos,
            'valor_m2': valor_m2_tipos
        },
        {
            'preco_medio_tipo': None,
            'quantidade': '',
            'tipo': 'Total',
            'm2': m2_total,
            'valor_venda': venda_total,
            'valor_m2': valor_m2_total
        }
    ]


    return render(request, 'bliss/summary.html', {
        'resumo': resumo,
        'totais': {
            'valor_tabela': total_valor_tabela,
            'valor_venda': total_valor_venda,
            'unidades': total_unidades,
        },
        'resumo_lojas': resumo_lojas,
    })

def atualizar_situacoes(request):
    updates = {
        'QA': [
            ('1-SUN', '201-SUN'),
            ('1-SUN', '206-SUN'),
            ('2-SHINE', '501-SHINE'),
        ],
        'Bloqueada': [
            ('1-SUN', '306-SUN'),
            ('1-SUN', '406-SUN'),
            ('2-SHINE', '305-SHINE'),
            ('2-SHINE', '405-SHINE'),
        ],
        'Permuta': [
            ('1-SUN', '101-SUN'),
            ('1-SUN', '303-SUN'),
            ('1-SUN', '505-SUN'),
            ('1-SUN', '701-SUN'),
            ('1-SUN', '802-SUN'),
            ('2-SHINE', '102-SHINE'),
            ('2-SHINE', '302-SHINE'),
            ('2-SHINE', '401-SHINE'),
            ('2-SHINE', '703-SHINE'),
        ],
        'Permuta/Venda': [
            ('1-SUNxxx', 'Loja'),
        ]
    }

    total_atualizados = 0

    for situacao, unidades in updates.items():
        for bloco, unidade in unidades:
            obj = Bliss.objects.filter(bloco=bloco, unidade=unidade).first()
            if obj:
                obj.situacao = situacao
                obj.save()
                total_atualizados += 1

    messages.success(request, f'{total_atualizados} registros atualizados com sucesso.')
    return redirect('bliss_unidades')

# Importar planilha Excel
def bliss_import(request):
    
    if request.method == 'POST' and request.FILES['excel_file']:
        excel_file = request.FILES['excel_file']
        wb = load_workbook(excel_file)
        ws = wb.active

        linhas=0
        for row in ws.iter_rows(min_row=2, values_only=True):
            linhas += 1 
            if linhas > 85:
                break
            if not row[0]:  # pula linhas vazias
                continue
            Bliss.objects.using('default').create(
                bloco=row[0],
                unidade=row[1],
                area_privativa=row[2],
                garagem=row[3],
                deposito=row[4],
                tipologia=row[5],
                situacao=row[6],
                valor_tabela=row[7] or 0,
                data_venda=row[8] if isinstance(row[8], datetime.date) else None,
                valor_venda=row[9] or 0,
                cliente=row[10] or '',
                email=row[11] or ''
            )
        return redirect('bliss_unidades')
    return render(request, 'bliss/bliss_import.html')


EXCECOES = {
    ('1-SUN', '201-SUN'),
    ('1-SUN', '206-SUN'),
    ('2-SHINE', '501-SHINE'),
    ('1-SUN', '306-SUN'),
    ('1-SUN', '406-SUN'),
    ('2-SHINE', '305-SHINE'),
    ('2-SHINE', '405-SHINE'),
    ('1-SUN', '101-SUN'),
    ('1-SUN', '303-SUN'),
    ('1-SUN', '505-SUN'),
}
EXCECOES = {}

def _parse_money_br(valor_str):
    if valor_str is None:
        return Decimal('0')
    s = str(valor_str).strip()
    if not s:
        return Decimal('0')
    s = s.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return Decimal('0')

def _get_ci(row, key_lower):
    # getter case-insensitive para DictReader
    for k, v in row.items():
        if k and k.lower().strip() == key_lower:
            return v
    return None

@transaction.atomic
def atualizacao_mensal(request):
    """
    Atualiza valor_tabela e situacao casando por (bloco, unidade).
    Aceita delimitadores ; , \t | e cabeÃ§alhos em qualquer ordem:
    bloco, unidade, valor_tabela, situacao
    """
    if request.method == 'POST' and request.FILES.get('csv_file'):
        f = request.FILES['csv_file']

        # decodifica respeitando BOM
        wrapper = io.TextIOWrapper(f.file, encoding='utf-8-sig', newline='')
        sample = wrapper.read(2048)
        wrapper.seek(0)

        # tenta detectar o delimitador; se falhar, forÃ§a ';'
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=';,|\t')
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ';'

        reader = csv.DictReader(wrapper, delimiter=delimiter)
        if not reader.fieldnames:
            messages.error(request, 'NÃ£o foi possÃ­vel ler os cabeÃ§alhos do CSV.')
            return redirect('bliss_unidades')

        obrigatorios = {'bloco', 'unidade', 'valor_tabela', 'situacao'}
        faltando = obrigatorios - {h.lower().strip() for h in reader.fieldnames if h}
        if faltando:
            messages.error(request, f'CabeÃ§alhos ausentes no CSV: {", ".join(sorted(faltando))}.')
            return redirect('bliss_unidades')

        total = puladas_excecao = nao_encontradas = sem_mudanca = 0
        objetos_para_update = []

        for row in reader:
            # pula linhas totalmente vazias
            if not any((row or {}).values()):
                continue

            total += 1
            bloco = (_get_ci(row, 'bloco') or '').strip()
            unidade = (_get_ci(row, 'unidade') or '').strip()
            if not bloco or not unidade:
                continue

            if (bloco, unidade) in EXCECOES:
                puladas_excecao += 1
                continue

            valor_tabela_csv = _parse_money_br(_get_ci(row, 'valor_tabela'))
            situacao_csv = (_get_ci(row, 'situacao') or '').strip()

            obj = Bliss.objects.filter(bloco=bloco, unidade=unidade).first()
            if not obj:
                nao_encontradas += 1
                continue

            mudou = False
            if obj.valor_tabela != valor_tabela_csv:
                obj.valor_tabela = valor_tabela_csv
                mudou = True
            if (obj.situacao or '') != situacao_csv:
                obj.situacao = situacao_csv
                mudou = True

            if mudou:
                objetos_para_update.append(obj)
            else:
                sem_mudanca += 1

        if objetos_para_update:
            Bliss.objects.bulk_update(objetos_para_update, ['valor_tabela', 'situacao'])

        messages.success(
            request,
            (
                f'Processadas: {total}. '
                f'Atualizadas: {len(objetos_para_update)}. '
                f'Sem mudanÃ§a: {sem_mudanca}. '
                f'Puladas (exceÃ§Ãµes): {puladas_excecao}. '
                f'NÃ£o encontradas: {nao_encontradas}. '
                f'(Delimitador detectado: "{delimiter}")'
            )
        )
        return redirect('bliss_unidades')

    return render(request, 'bliss/bliss_atualizacao_mensal.html')

def _build_bliss_resumo_context():
    registros = list(Bliss.objects.all())

    situacao = {
        'Disponível': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')},
        'Reservada': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')},
        'Bloqueada': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')}, 
        'Vendida': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')},
        'Permuta': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')},
        'QA': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')},
        'Total': {'qtde': 0, 'valor': Decimal('0'), 'area': Decimal('0')},
    }

    status_labels = [label for label in situacao.keys() if label != 'Total']

    def normalizar_status(valor: str) -> str:
        if not valor:
            return ''
        base = unicodedata.normalize('NFKD', valor.strip())
        sem_acentos = ''.join(ch for ch in base if not unicodedata.combining(ch))
        return sem_acentos.casefold()

    status_lookup: dict[str, str] = {}

    def registrar_lookup(label: str) -> None:
        chave_norm = normalizar_status(label)
        if not chave_norm:
            return
        if chave_norm not in status_lookup:
            status_lookup[chave_norm] = label
        chave_lower = label.strip().casefold()
        if chave_lower not in status_lookup:
            status_lookup[chave_lower] = label

    for label in status_labels:
        registrar_lookup(label)

    status_disponivel_norm = normalizar_status('Disponivel')

    agrupadas = {label: [] for label in status_labels}
    fator_permuta = Decimal('0.12826')
    fator_restante = Decimal('0.87174')

    def adicionar_unidade(label, valor_calculado, area_calculada, registro):
        label = (label or '').strip()
        if not label:
            return
        chave_norm = normalizar_status(label)
        chave_mapeada = status_lookup.get(chave_norm) or status_lookup.get(label.casefold()) or label
        registrar_lookup(chave_mapeada)
        agrupadas.setdefault(chave_mapeada, []).append({
            'id': registro.id,
            'bloco': registro.bloco,
            'unidade': registro.unidade,
            'situacao': chave_mapeada,
            'valor_tabela': valor_calculado,
            'area_privativa': area_calculada,
            'garagem': registro.garagem,
            'deposito': registro.deposito,
            'tipologia': registro.tipologia,
        })

    for registro in registros:
        valor = registro.valor_tabela or Decimal('0')
        area = registro.area_privativa or Decimal('0')
        unidade_nome = (registro.unidade or '').strip().lower()
        situacao_registro = (registro.situacao or '').strip()

        if unidade_nome == 'loja':
            adicionar_unidade('Permuta', valor * fator_permuta, area * fator_permuta, registro)
            adicionar_unidade(situacao_registro, valor * fator_restante, area * fator_restante, registro)
        else:
            adicionar_unidade(situacao_registro, valor, area, registro)

    def ordenar_unidades(itens):
        return sorted(
            itens,
            key=lambda item: (
                (item.get('bloco') or ''),
                (item.get('unidade') or ''),
            ),
        )

    unidades = [
        {'situacao': label, 'unidades': ordenar_unidades(agrupadas.get(label, []))}
        for label in status_labels
    ]

    extras = [label for label in agrupadas.keys() if label not in status_labels]
    for label in extras:
        registrar_lookup(label)
        unidades.append({'situacao': label, 'unidades': ordenar_unidades(agrupadas[label])})

    default_totais = {
        'qtde': 0,
        'valor': Decimal('0'),
        'area': Decimal('0'),
        'qtde_perc': Decimal('0'),
        'valor_perc': Decimal('0'),
    }
    unidades = [
        {**item, 'totais': situacao.get(item['situacao'], default_totais)}
        for item in unidades
    ]
    unidades_por_status = {item['situacao']: item['unidades'] for item in unidades}

    def to_float(value):
        if value is None:
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            try:
                return float(str(value).replace(',', '.'))
            except (TypeError, ValueError):
                return 0.0

    resumo = {
        'preco_medio_tipo': 0,
        'qtde_lojas': 0,
        'qtde_tipos': 0,
        'qtde_total': 0,

        'valor_loja': 0,
        'valor_tipos': 0,
        'valor_total': 0,

        'priv_loja': 0,
        'priv_tipos': 0,
        'priv_avenda': 0,

        'm2_loja': 0,
        'm2_tipos': 0,
        'm2_avenda': 0,
    }

    for registro in registros:
        chave = (registro.situacao or '').strip()
        valor = registro.valor_tabela or Decimal('0')
        area = registro.area_privativa or Decimal('0')

        if registro.unidade == 'Loja':
            valor_permuta = valor * fator_permuta
            valor_restante = valor * fator_restante
            area_permuta = area * fator_permuta
            area_restante = area * fator_restante

            situacao["Permuta"]['qtde'] += 1
            situacao["Permuta"]['valor'] += valor_permuta
            situacao["Permuta"]['area'] += area_permuta

            destino = (registro.situacao or '').strip()
            destino_normalizado = status_lookup.get(destino.casefold(), destino) if destino else ''
            if destino_normalizado:
                if destino_normalizado not in situacao:
                    situacao[destino_normalizado] = {
                        'qtde': 0,
                        'valor': Decimal('0'),
                        'area': Decimal('0'),
                    }
                    registrar_lookup(destino_normalizado)
                situacao[destino_normalizado]['qtde'] += 1
                situacao[destino_normalizado]['valor'] += valor_restante
                situacao[destino_normalizado]['area'] += area_restante

            if normalizar_status(destino_normalizado) == status_disponivel_norm:
                resumo["qtde_lojas"] = 1
                resumo["valor_loja"] = valor_restante
                resumo["priv_loja"] = area_restante

        else:
            if chave and chave not in situacao:
                situacao[chave] = {
                    'qtde': 0,
                    'valor': Decimal('0'),
                    'area': Decimal('0'),
                }
                registrar_lookup(chave)
            if chave in situacao:
                situacao[chave]['qtde'] += 1
                situacao[chave]['valor'] += valor
                situacao[chave]['area'] += area
                if normalizar_status(registro.situacao) == status_disponivel_norm:
                    resumo["qtde_tipos"] += 1
                    resumo["priv_tipos"] += area
                    resumo["valor_tipos"] += registro.valor_tabela
        situacao['Total']['qtde'] += 1
        situacao['Total']['valor'] += valor
        situacao['Total']['area'] += area

    total_qtde = situacao['Total']['qtde']
    total_valor = situacao['Total']['valor']

    if resumo["qtde_tipos"]:
        resumo["preco_medio_tipo"] = resumo["valor_tipos"] / resumo["qtde_tipos"]
    else:
        resumo["preco_medio_tipo"] = 0    

    if resumo["priv_loja"]:
        resumo["m2_loja"] = resumo["valor_loja"] / resumo["priv_loja"] 
    else:
        resumo["m2_loja"] = 0   

    if resumo["priv_tipos"]:
        resumo["m2_tipos"] = resumo["valor_tipos"] / resumo["priv_tipos"] 
    else:
        resumo["m2_tipos"] = 0 

    resumo["qtde_total"] = resumo["qtde_lojas"] + resumo["qtde_tipos"]  
    resumo["valor_total"] = resumo["valor_loja"] + resumo["valor_tipos"] 
    resumo["priv_total"] = resumo["priv_loja"] + resumo["priv_tipos"] 

    if resumo["priv_total"]:
        resumo["m2_total"] = resumo["valor_total"] / resumo["priv_total"] 
    else:
        resumo["m2_total"] = 0 

    for dados in situacao.values():
        dados['qtde_perc'] = (Decimal(dados['qtde']) / Decimal(total_qtde) * Decimal('100')) if total_qtde else Decimal('0')
        dados['valor_perc'] = (dados['valor'] / total_valor * Decimal('100')) if total_valor else Decimal('0')
        dados['area_perc'] = (dados['area'] / situacao['Total']['area'] * Decimal('100')) if situacao['Total']['area'] else Decimal('0')

    chart_data = {
        'situacao_labels': [item['situacao'] for item in unidades],
        'situacao_valores': [to_float((situacao.get(item['situacao']) or {}).get('valor')) for item in unidades],
        'situacao_areas': [to_float((situacao.get(item['situacao']) or {}).get('area')) for item in unidades],
        'situacao_qtdes': [int((situacao.get(item['situacao']) or {}).get('qtde') or 0) for item in unidades],
        'tipo_labels': ['Tipos', 'Lojas'],
        'tipo_valores': [to_float(resumo.get('valor_tipos')), to_float(resumo.get('valor_loja'))],
        'tipo_areas': [to_float(resumo.get('priv_tipos')), to_float(resumo.get('priv_loja'))],
    }


    return {
        'situacao': situacao,
        'registros': registros,
        'unidades': unidades,
        'chart_data': chart_data,
        'unidades_por_status': unidades_por_status,
        'resumo': resumo,
    }

def _render_bliss_resumo_pdf(context):
    template = get_template('bliss/bliss_resumo_pdf.html')
    html = template.render(context)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=buffer)
    if pisa_status.err:
        raise ValueError('Erro ao gerar PDF do resumo Bliss')
    buffer.seek(0)
    return buffer


def send_bliss_resumo_pdf_email(recipient_email, *, subject=None, body=None):
    context = _build_bliss_resumo_context()
    pdf_buffer = _render_bliss_resumo_pdf(context)
    email = EmailMessage(
        subject or 'Resumo Bliss',
        body or 'Segue em anexo o resumo Bliss.',
        to=[recipient_email],
    )
    email.attach('bliss_resumo.pdf', pdf_buffer.getvalue(), 'application/pdf')
    sent_count = email.send(fail_silently=False)
    if sent_count == 0:
        raise ValueError('Nenhum e-mail foi enviado.')


def _attach_email_flag(request, context):
    sent_info = request.session.get('bliss_resumo_email_sent')
    email_flag = False
    if isinstance(sent_info, dict):
        ts = sent_info.get('ts')
        if ts and (time.time() - ts) <= 5:
            email_flag = sent_info.get('email') or True
        else:
            request.session.pop('bliss_resumo_email_sent', None)
    elif sent_info:
        email_flag = True
        request.session.pop('bliss_resumo_email_sent', None)
    context['email_enviado'] = email_flag
    return context


def bliss_resumo(request):
    context = _attach_email_flag(request, _build_bliss_resumo_context())
    return render(request, 'bliss/bliss_resumo.html', context)


def bliss_resumo_novo(request):
    context = _attach_email_flag(request, _build_bliss_resumo_context())
    return render(request, 'bliss/bliss_resumo_novo.html', context)

def bliss_dashboard(request):
    context = _attach_email_flag(request, _build_bliss_resumo_context())
    return render(request, 'bliss/bliss_dashboard.html', context)

def bliss_resumo_pdf(request):
    context = _build_bliss_resumo_context()
    try:
        pdf_buffer = _render_bliss_resumo_pdf(context)
    except ValueError as exc:
        return HttpResponse(str(exc), status=500)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bliss_resumo.pdf"'
    response.write(pdf_buffer.getvalue())
    return response


@csrf_exempt
def bliss_resumo_email_webhook(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Metodo nao permitido'}, status=405)

    try:
        raw_body = request.body.decode('utf-8') if request.body else ''
        payload = json.loads(raw_body) if raw_body else {}
    except json.JSONDecodeError:
        payload = request.POST

    email = (payload.get('email') or payload.get('to') or '').strip()
    password = (payload.get('senha') or payload.get('password') or '').strip()

    if password != WEBHOOK_PASSWORD:
        return JsonResponse({'detail': 'Credenciais invalidas'}, status=403)

    if not email:
        return JsonResponse({'detail': 'E-mail nao informado'}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'detail': 'E-mail invalido'}, status=400)

    try:
        send_bliss_resumo_pdf_email(email)
    except ValueError as exc:
        return JsonResponse({'detail': str(exc)}, status=500)
    except Exception:
        return JsonResponse({'detail': 'Erro inesperado ao enviar o e-mail'}, status=500)

    return JsonResponse({'status': 'ok'})


@login_required
def bliss_resumo_send_email(request):
    if request.method != 'POST':
        return redirect('bliss_resumo')

    email = (request.user.email or '').strip()
    if not email:
        messages.error(request, 'Seu usuario nao possui e-mail cadastrado.')
        return redirect('bliss_resumo')

    try:
        send_bliss_resumo_pdf_email(email)
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception:
        messages.error(request, 'Nao foi possivel enviar o resumo por e-mail.')
    else:
        messages.success(request, f'Resumo enviado para {email}.')
        request.session['bliss_resumo_email_sent'] = {'email': email, 'ts': time.time()}

    return redirect('bliss_resumo')


@csrf_exempt
def bliss_resumo_test_email(request):
    if request.method not in ('POST', 'GET'):
        return JsonResponse({'detail': 'Metodo nao permitido'}, status=405)

    if request.method == 'GET':
        payload = request.GET
    else:
        try:
            raw_body = request.body.decode('utf-8') if request.body else ''
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            payload = request.POST

    email = (payload.get('email') or '').strip()
    password = (payload.get('senha') or payload.get('password') or '').strip()

    if password != WEBHOOK_PASSWORD:
        return JsonResponse({'detail': 'Credenciais invalidas'}, status=403)

    if not email:
        return JsonResponse({'detail': 'E-mail nao informado'}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'detail': 'E-mail invalido'}, status=400)

    email_message = EmailMessage(
        'Teste de envio Bliss',
        'Este e um e-mail de teste do sistema Bliss.',
        to=[email],
    )

    try:
        sent = email_message.send(fail_silently=False)
    except Exception:
        return JsonResponse({'detail': 'Erro ao enviar e-mail de teste'}, status=500)

    if sent == 0:
        return JsonResponse({'detail': 'Nenhum e-mail foi enviado'}, status=500)

    return JsonResponse({'status': 'ok', 'message': 'E-mail de teste enviado'})






