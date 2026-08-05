from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .services import MODELO_PADRAO, MODELOS_DISPONIVEIS, AssistenteError, perguntar


def _apenas_admin(request):
    return request.user.is_authenticated and request.user.groups.filter(name='admin').exists()


@login_required
def pesquisa(request):
    if not _apenas_admin(request):
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')

    pergunta = ''
    modelo = MODELO_PADRAO
    resposta = None
    erro = None

    if request.method == 'POST':
        pergunta = request.POST.get('pergunta', '').strip()
        modelo = request.POST.get('modelo', MODELO_PADRAO)
        if modelo not in MODELOS_DISPONIVEIS:
            modelo = MODELO_PADRAO
        try:
            resposta = perguntar(pergunta, modelo=modelo)
        except AssistenteError as exc:
            erro = str(exc)
        except Exception as exc:
            erro = f'Erro ao consultar o assistente: {exc}'

    return render(request, 'assistente/pesquisa.html', {
        'pergunta': pergunta,
        'modelo': modelo,
        'modelos_disponiveis': MODELOS_DISPONIVEIS.items(),
        'resposta': resposta,
        'erro': erro,
    })
