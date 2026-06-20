from django.urls import reverse, NoReverseMatch
from .models import MenuItem, EmpresaMenuItem, UsuarioEmpresa


def menu_acesso(request):
    if not request.user or not request.user.is_authenticated:
        return {'menu_permitido': set(), 'menu_itens': {}, 'menu_principal': {}}

    # ── IDs dos MenuItems acessíveis (por PK, não por url_name) ─────────────
    if request.user.is_superuser:
        allowed_ids = set(MenuItem.objects.filter(ativo=True).values_list('pk', flat=True))
    else:
        allowed_ids = set()
        vinculos = UsuarioEmpresa.objects.filter(user=request.user).prefetch_related('itens', 'empresa')
        for vinculo in vinculos:
            empresa_ids = set(
                EmpresaMenuItem.objects
                .filter(empresa=vinculo.empresa, ativo=True)
                .values_list('menu_item_id', flat=True)
            )
            usuario_ids = set(vinculo.itens.values_list('pk', flat=True))
            allowed_ids |= empresa_ids & usuario_ids

    # url_names permitidos (para uso em templates: {% if 'bliss_resumo' in menu_permitido %})
    menu_permitido = set(
        MenuItem.objects.filter(pk__in=allowed_ids).values_list('url_name', flat=True)
    )

    # ── monta menu_itens (secundárias) e menu_principal (principal agrupado) ──
    menu_itens    = {}
    menu_principal = {}

    qs = MenuItem.objects.filter(pk__in=allowed_ids, ativo=True).order_by('app', 'navbar', 'ordem')
    for item in qs:
        try:
            url = reverse(item.url_name)
        except NoReverseMatch:
            url = '#'

        entry = {
            'label':         item.label,
            'url':           url,
            'url_name':      item.url_name,
            'url_name_base': item.url_name.split(':')[-1],
            'icon':          item.icon,
        }

        if item.app == 'intranet' and item.navbar == 'principal':
            if item.grupo == 'admin':
                menu_principal.setdefault('admin', []).append(entry)
            elif item.grupo == 'gerencial':
                # Gerencial: agrupado por subgrupo para exibir divisórias
                menu_principal.setdefault('gerencial', {}) \
                              .setdefault(item.subgrupo or 'geral', []) \
                              .append(entry)
            elif item.grupo:
                menu_principal.setdefault(item.grupo, []).append(entry)
        else:
            menu_itens \
                .setdefault(item.app, {}) \
                .setdefault(item.navbar, []) \
                .append(entry)

    return {
        'menu_permitido': menu_permitido,
        'menu_itens':     menu_itens,
        'menu_principal': menu_principal,
    }
