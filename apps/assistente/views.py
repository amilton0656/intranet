from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .services import AssistenteError, perguntar


def _apenas_admin(request):
    return request.user.is_authenticated and request.user.groups.filter(name='admin').exists()


@login_required
def pesquisa(request):
    if not _apenas_admin(request):
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')

    pergunta = ''
    resposta = None
    erro = None

    if request.method == 'POST':
        pergunta = request.POST.get('pergunta', '').strip()
        try:
            resposta = perguntar(pergunta)
        except AssistenteError as exc:
            erro = str(exc)
        except Exception as exc:
            erro = f'Erro ao consultar o assistente: {exc}'

    return render(request, 'assistente/pesquisa.html', {
        'pergunta': pergunta,
        'resposta': resposta,
        'erro': erro,
    })
