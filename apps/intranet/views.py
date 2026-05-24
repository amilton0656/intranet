import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from uteis import Uteis


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
