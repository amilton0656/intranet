from datetime import date

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Pessoa
from .forms import PessoaForm
from .utils import render_to_pdf


@login_required
def pessoa_list(request):
    pessoas = Pessoa.objects.all()

    f_nome  = request.GET.get('nome', '').strip()
    f_papel = request.GET.get('papel', '').strip()
    f_tipo  = request.GET.get('tipo', '').strip()
    f_ativo = request.GET.get('ativo', '').strip()

    if f_nome:
        pessoas = pessoas.filter(nome__icontains=f_nome)
    if f_tipo:
        pessoas = pessoas.filter(tipo=f_tipo)
    if f_papel == 'cliente':
        pessoas = pessoas.filter(is_cliente=True)
    elif f_papel == 'corretor':
        pessoas = pessoas.filter(is_corretor=True)
    elif f_papel == 'imobiliaria':
        pessoas = pessoas.filter(is_imobiliaria=True)
    elif f_papel == 'fornecedor':
        pessoas = pessoas.filter(is_fornecedor=True)
    elif f_papel == 'outro':
        pessoas = pessoas.filter(is_outro=True)
    if f_ativo == '1':
        pessoas = pessoas.filter(ativo=True)
    elif f_ativo == '0':
        pessoas = pessoas.filter(ativo=False)

    filtros_ativos = any([f_nome, f_papel, f_tipo, f_ativo])

    return render(request, 'pessoas/pessoa_list.html', {
        'pessoas':        pessoas,
        'tipo_choices':   Pessoa.TIPO_CHOICES,
        'filtros':        {'nome': f_nome, 'papel': f_papel, 'tipo': f_tipo, 'ativo': f_ativo},
        'filtros_ativos': filtros_ativos,
    })


@login_required
def pessoa_create(request):
    form = PessoaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Pessoa cadastrada com sucesso.')
        return redirect('pessoas:pessoa_list')
    return render(request, 'pessoas/pessoa_form.html', {'form': form, 'titulo': 'Nova Pessoa'})


@login_required
def pessoa_edit(request, pk):
    pessoa = get_object_or_404(Pessoa, pk=pk)
    form = PessoaForm(request.POST or None, instance=pessoa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Pessoa atualizada com sucesso.')
        return redirect('pessoas:pessoa_list')
    return render(request, 'pessoas/pessoa_form.html', {
        'form': form, 'titulo': 'Editar Pessoa', 'obj': pessoa,
    })


@login_required
def pessoa_list_pdf(request):
    pessoas = Pessoa.objects.all()

    f_nome  = request.GET.get('nome', '').strip()
    f_papel = request.GET.get('papel', '').strip()
    f_tipo  = request.GET.get('tipo', '').strip()
    f_ativo = request.GET.get('ativo', '').strip()

    if f_nome:
        pessoas = pessoas.filter(nome__icontains=f_nome)
    if f_tipo:
        pessoas = pessoas.filter(tipo=f_tipo)
    if f_papel == 'cliente':
        pessoas = pessoas.filter(is_cliente=True)
    elif f_papel == 'corretor':
        pessoas = pessoas.filter(is_corretor=True)
    elif f_papel == 'imobiliaria':
        pessoas = pessoas.filter(is_imobiliaria=True)
    elif f_papel == 'fornecedor':
        pessoas = pessoas.filter(is_fornecedor=True)
    elif f_papel == 'outro':
        pessoas = pessoas.filter(is_outro=True)
    if f_ativo == '1':
        pessoas = pessoas.filter(ativo=True)
    elif f_ativo == '0':
        pessoas = pessoas.filter(ativo=False)

    partes = []
    if f_papel:
        partes.append(f_papel.capitalize())
    if f_tipo:
        partes.append(dict(Pessoa.TIPO_CHOICES).get(f_tipo, f_tipo))
    if f_nome:
        partes.append(f'"{f_nome}"')
    if f_ativo == '1':
        partes.append('Ativos')
    elif f_ativo == '0':
        partes.append('Inativos')
    subtitulo = ' · '.join(partes) if partes else ''

    return render_to_pdf('pessoas/pdf/pessoa_list.html', {
        'pessoas': list(pessoas),
        'subtitulo': subtitulo,
        'data': date.today().strftime('%d/%m/%Y'),
    }, filename='pessoas.pdf')


@login_required
def pessoa_delete(request, pk):
    pessoa = get_object_or_404(Pessoa, pk=pk)
    if request.method == 'POST':
        pessoa.delete()
        messages.success(request, 'Pessoa excluída com sucesso.')
        return redirect('pessoas:pessoa_list')
    return render(request, 'pessoas/pessoa_confirm_delete.html', {'obj': pessoa})
