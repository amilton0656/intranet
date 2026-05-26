import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from uteis import Uteis

GRUPOS_DISPONIVEIS = [
    ('admin',        'Admin',        'Acesso total — todos os menus'),
    ('manager',      'Gerencial',    'Tabelas de Vendas e Gerencial'),
    ('financeiro',   'Financeiro',   'Menu Financeiro (Bliss / Cota 365)'),
    ('incorporadora','Incorporadora','App Incorporadora'),
]


@login_required
def intranet_home(request):
    uteis = Uteis()
    cubs = uteis.cubs_hoje()
    cubs_history = uteis.fetch_indices_last_12_months()

    context = {
        'cubs': cubs,
        'cubs_history': cubs_history,
    }

    return render(request, 'intranet/intranet_home.html', context)


@login_required
def financeiro_home(request):
    if not request.user.groups.filter(name__in=['admin', 'financeiro']).exists():
        messages.error(request, 'Acesso restrito ao grupo Financeiro.')
        return redirect('intranet_home')
    return render(request, 'intranet/financeiro_home.html')


@login_required
def upload_pdfs(request):
    if not request.user.groups.filter(name='admin').exists():
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')

    downloads_dir = settings.MEDIA_ROOT / 'downloads'
    downloads_dir.mkdir(parents=True, exist_ok=True)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'upload':
            arquivo = request.FILES.get('arquivo')
            if not arquivo:
                messages.error(request, 'Nenhum arquivo selecionado.')
            elif not arquivo.name.lower().endswith('.pdf'):
                messages.error(request, 'Apenas arquivos PDF são permitidos.')
            else:
                destino = downloads_dir / arquivo.name
                with open(destino, 'wb') as f:
                    for chunk in arquivo.chunks():
                        f.write(chunk)
                messages.success(request, f'"{arquivo.name}" enviado com sucesso.')

        elif action == 'delete':
            nome = request.POST.get('nome', '')
            if nome and not ('/' in nome or '\\' in nome):
                alvo = downloads_dir / nome
                if alvo.exists():
                    alvo.unlink()
                    messages.success(request, f'"{nome}" excluído.')
                else:
                    messages.error(request, f'Arquivo "{nome}" não encontrado.')

        return redirect('intranet_uploads')

    pdfs = sorted(
        [
            {
                'nome': f.name,
                'tamanho': f'{f.stat().st_size / 1024:.1f} KB',
                'url': f'{settings.MEDIA_URL}downloads/{f.name}',
            }
            for f in downloads_dir.iterdir()
            if f.is_file() and f.suffix.lower() == '.pdf'
        ],
        key=lambda x: x['nome'],
    )

    return render(request, 'intranet/intranet_uploads.html', {'pdfs': pdfs})


def _apenas_admin(request):
    return request.user.is_authenticated and request.user.groups.filter(name='admin').exists()


@login_required
def usuario_list(request):
    if not _apenas_admin(request):
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')
    usuarios = User.objects.prefetch_related('groups').order_by('first_name', 'username')
    return render(request, 'intranet/usuario_list.html', {
        'usuarios': usuarios,
        'grupos_disponiveis': GRUPOS_DISPONIVEIS,
    })


@login_required
def usuario_edit(request, pk):
    if not _apenas_admin(request):
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        novos_grupos = request.POST.getlist('grupos')
        grupos_obj = []
        for nome, _, _ in GRUPOS_DISPONIVEIS:
            grupo, _ = Group.objects.get_or_create(name=nome)
            if nome in novos_grupos:
                grupos_obj.append(grupo)
        usuario.groups.set(grupos_obj)
        messages.success(request, f'Grupos de "{usuario.get_full_name() or usuario.username}" atualizados.')
        return redirect('usuario_list')
    grupos_atuais = set(usuario.groups.values_list('name', flat=True))
    return render(request, 'intranet/usuario_form.html', {
        'usuario': usuario,
        'grupos_disponiveis': GRUPOS_DISPONIVEIS,
        'grupos_atuais': grupos_atuais,
    })
