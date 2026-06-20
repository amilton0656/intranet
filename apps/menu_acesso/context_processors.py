from django.urls import reverse, NoReverseMatch
from .models import MenuItem


def menu_acesso(request):
    if not request.user or not request.user.is_authenticated:
        return {'menu_permitido': set(), 'menu_itens': {}}

    # ── itens acessíveis (url_names) ──────────────────────────────────────────
    if request.user.is_superuser:
        qs_permitido = MenuItem.objects.filter(ativo=True)
    else:
        user_groups = request.user.groups.values_list('pk', flat=True)
        qs_permitido = MenuItem.objects.filter(ativo=True).filter(
            grupos__pk__in=user_groups
        ).union(
            MenuItem.objects.filter(ativo=True, usuarios=request.user)
        )

    menu_permitido = set(qs_permitido.values_list('url_name', flat=True))

    # ── itens agrupados por app > navbar (apenas os acessíveis ao usuário) ───
    menu_itens = {}
    qs_itens = MenuItem.objects.filter(ativo=True, url_name__in=menu_permitido).order_by('app', 'navbar', 'ordem')
    for item in qs_itens:
        try:
            url = reverse(item.url_name)
        except NoReverseMatch:
            url = '#'

        url_name_base = item.url_name.split(':')[-1]

        menu_itens \
            .setdefault(item.app, {}) \
            .setdefault(item.navbar, []) \
            .append({
                'label':         item.label,
                'url':           url,
                'url_name':      item.url_name,
                'url_name_base': url_name_base,
                'icon':          item.icon,
            })

    return {
        'menu_permitido': menu_permitido,
        'menu_itens':     menu_itens,
    }
