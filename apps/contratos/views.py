import io

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from docxtpl import DocxTemplate

from apps.propostas.models import Proposta
from .models import MinutaContrato
from .forms import MinutaContratoForm
from .context import build_context


# ── CRUD de Minutas ───────────────────────────────────────────────────────────

@login_required
def minuta_list(request):
    minutas = MinutaContrato.objects.all()
    return render(request, 'contratos/minuta_list.html', {'minutas': minutas})


@login_required
def minuta_create(request):
    form = MinutaContratoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Minuta cadastrada com sucesso.')
        return redirect('contratos:minuta_list')
    return render(request, 'contratos/minuta_form.html', {'form': form, 'titulo': 'Nova Minuta'})


@login_required
def minuta_edit(request, pk):
    minuta = get_object_or_404(MinutaContrato, pk=pk)
    form = MinutaContratoForm(request.POST or None, request.FILES or None, instance=minuta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Minuta atualizada com sucesso.')
        return redirect('contratos:minuta_list')
    return render(request, 'contratos/minuta_form.html', {
        'form': form, 'titulo': 'Editar Minuta', 'obj': minuta,
    })


@login_required
def minuta_delete(request, pk):
    minuta = get_object_or_404(MinutaContrato, pk=pk)
    if request.method == 'POST':
        minuta.delete()
        messages.success(request, 'Minuta excluída.')
        return redirect('contratos:minuta_list')
    return render(request, 'contratos/minuta_confirm_delete.html', {'obj': minuta})


# ── Geração de Contrato ───────────────────────────────────────────────────────

@login_required
def contrato_gerar(request, numero):
    proposta = get_object_or_404(Proposta, numero=numero)
    minutas  = MinutaContrato.objects.filter(ativo=True)

    if request.method == 'POST':
        minuta_pk = request.POST.get('minuta')
        minuta = get_object_or_404(MinutaContrato, pk=minuta_pk, ativo=True)

        ctx = build_context(proposta)

        tpl = DocxTemplate(minuta.arquivo.path)
        tpl.render(ctx)

        buffer = io.BytesIO()
        tpl.save(buffer)
        buffer.seek(0)

        nome_arquivo = f'contrato_{proposta.numero}.docx'
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        )
        response['Content-Disposition'] = f'attachment; filename="{nome_arquivo}"'
        return response

    return render(request, 'contratos/contrato_gerar.html', {
        'proposta': proposta,
        'minutas':  minutas,
    })
