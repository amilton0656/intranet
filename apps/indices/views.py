from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.urls import reverse
from .models import Indice, IndiceData
from .forms import IndiceForm, IndiceDataForm
from datetime import date

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db import connection
from django.db import connections
from django.http import JsonResponse

from dotenv import load_dotenv

# ---------------- Indice ----------------

def indice_list(request):
    q = request.GET.get('q', '').strip()
    qs = Indice.objects.all()
    if q:
        qs = qs.filter(Q(descricao__icontains=q))

    paginator = Paginator(qs, 10)
    page = request.GET.get('page')
    object_list = paginator.get_page(page)

    return render(request, 'indices/indice_list.html', {
        'object_list': object_list,
        'page_title': 'Lista de índices'
        })


def indice_create(request):
    if request.method == 'POST':
        form = IndiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Índice criado com sucesso!')
            return redirect('indices:indice_list')
    else:
        form = IndiceForm()
    return render(request, 'indices/indice_form.html', {
        'form': form,
        'page_title': 'Novo índice'
        })


def indice_update(request, pk):
    indice = get_object_or_404(Indice, pk=pk)
    if request.method == 'POST':
        form = IndiceForm(request.POST, instance=indice)
        if form.is_valid():
            form.save()
            messages.success(request, 'Índice atualizado com sucesso!')
            return redirect('indices:indice_list')
    else:
        form = IndiceForm(instance=indice)
    return render(request, 'indices/indice_form.html', {
        'form': form,
        'page_title': 'Editar índice'
        })


def indice_delete(request, pk):
    indice = get_object_or_404(Indice, pk=pk)
    if request.method == 'POST':
        indice.delete()
        messages.success(request, 'Índice excluído com sucesso!')
        return redirect('indices:indice_list')
    return render(request, 'indices/indice_confirm_delete.html', {
        'object': indice,
        'page_title': 'Excluir índice'
        })


# ---------------- IndiceData ----------------

def indicedata_list(request):
    q = request.GET.get('q', '').strip()
    indice_id = request.GET.get('indice')
    qs = IndiceData.objects.select_related('indice').all()

    if q:
        qs = qs.filter(
            Q(indice__descricao__icontains=q) |
            Q(data__icontains=q)
        )
    if indice_id:
        qs = qs.filter(indice_id=indice_id)

    paginator = Paginator(qs, 12)
    page = request.GET.get('page')
    object_list = paginator.get_page(page)

    indices = Indice.objects.all().order_by('descricao')

    return render(request, 'indices/indicedata_list.html', {
        'object_list': object_list,
        'indices': indices,
        'page_title': 'Lista dos valores'
    })


def buscar_indicedata_por_data(request, indice_id, data_str):
    """
    Busca um valor de IndiceData para um índice específico em uma data específica.

    URL esperada: /indices/valor/<indice_id>/<data_str>/
    Ex.: /indices/valor/5/2025-09-21/
    """
    # garante que o índice existe
    indice = get_object_or_404(Indice, pk=indice_id)

    # filtra registros com a data informada (string 'YYYY-MM-DD')
    qs = IndiceData.objects.filter(indice=indice, data=data_str)

    if not qs.exists():
        return JsonResponse({
            'success': False,
            'message': 'Nenhum valor encontrado para esta data.'
        }, status=404)

    # se houver mais de um, retorna todos; se for 1 só, retorna único
    dados = [
        {
            'id': obj.id,
            'indice': obj.indice.descricao,
            'data': obj.data.strftime('%Y-%m-%d'),
            'valor': obj.valor  # ajuste ao nome do campo de valor
        }
        for obj in qs
    ]
    return JsonResponse({'success': True, 'resultados': dados})

def indicedata_create(request):
    if request.method == 'POST':
        form = IndiceDataForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Valor do índice criado com sucesso!')
            return redirect('indices:indicedata_list')
    else:
        form = IndiceDataForm()
    return render(request, 'indices/indicedata_form.html', {
        'form': form,
        'page_title': 'Novo valor'
        })


def indicedata_update(request, pk):
    indicedata = get_object_or_404(IndiceData, pk=pk)
    if request.method == 'POST':
        form = IndiceDataForm(request.POST, instance=indicedata)
        if form.is_valid():
            form.save()
            messages.success(request, 'Valor do índice atualizado com sucesso!')
            return redirect('indices:indicedata_list')
    else:
        form = IndiceDataForm(instance=indicedata)
    return render(request, 'indices/indicedata_form.html', {
        'form': form,
        'page_title': 'Editar valor'
        })


def indicedata_delete(request, pk):
    indicedata = get_object_or_404(IndiceData, pk=pk)
    if request.method == 'POST':
        indicedata.delete()
        messages.success(request, 'Valor do índice excluído com sucesso!')
        return redirect('indices:indicedata_list')
    return render(request, 'indices/indicedata_confirm_delete.html', {
        'object': indicedata,
        'page_title': 'Excluir valor'
        })


# ---------------- SQL ----------------


def executar_sql(sql, params=None):
    """
    Executa uma query SQL crua e retorna uma lista de dicionários.
    - sql: string com a consulta (pode usar %s para parâmetros).
    - params: lista ou tupla com os valores para %s.
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        # pega os nomes das colunas
        columns = [col[0] for col in cursor.description]
        # converte cada linha para dicionário {coluna: valor}
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]


def buscar_valor_sql(request, indice_id, data_str):
    """
    Busca valores de IndiceData usando SQL cru.
    Ex.: /indices/valor-sql/5/2025-09-21/
    """
    sql = """
        SELECT id, indice_id, data, valor
        FROM indices_indicedata
        WHERE indice_id = %s AND data = %s
    """
    resultados = executar_sql(sql, [indice_id, data_str])

    if not resultados:
        return JsonResponse({'success': False, 'message': 'Nenhum registro encontrado.'}, status=404)

    return JsonResponse({'success': True, 'resultados': resultados})


def fetch_indices_data(id_indice, indice_data):
    """Fetch raw rows from indices_datas matching the given indice and date."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT *
            FROM indices_datas
            WHERE id_indice = %s AND data = %s
            """,
            [id_indice, indice_data],
        )
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]

def indices_detail(request):
    indice_data = date(2025, 9, 1)
    print("data ", indice_data)
    indices = fetch_indices_data(1, indice_data)
    return render(request, 'indices/postgres.html', {'valor': indices})


from django.db import connections
from django.shortcuts import render

def fetch_postgres(request, sql=None):
    query = sql or "select * from indices_datas"
    # 'reporting'   or   'default'
    with connections['default'].cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return render(request, 'indices/postgres.html', {'resposta': rows, 'valor': rows[0]["valor"]})


def cubs_hoje(request):
    hoje = date.today()
    data = date(hoje.year, hoje.month,1)

    indices1 = fetch_indices_data(1, data)
    indices2 = fetch_indices_data(2, data)
    indices3 = fetch_indices_data(1, data)
    indices4 = fetch_indices_data(2, data)
    return render(request, 'indices/postgres.html', {'valor1': indices1[0]['valor'], 'valor2': indices2[0]['valor'], 'valor3': indices3[0]['valor'], 'valor4': indices4[0]['valor']})