from django.shortcuts import render
from uteis import Uteis


def intranet_home(request):
    uteis = Uteis()
    cubs = uteis.cubs_hoje()
    cubs_history = uteis.fetch_indices_last_12_months()

    context = {
        'cubs': cubs,
        'cubs_history': cubs_history,
    }

    return render(request, 'intranet/intranet_home.html', context)
