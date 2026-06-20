from django.contrib import admin
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from .models import MenuItem, EmpresaMenuItem, UsuarioEmpresa


def _build_arvore(qs, habilitados):
    """
    Monta a árvore: Navbar Principal (topo) + apps secundários (ordem alfa).
    Intranet/principal agrupa por grupo ('Financeiro', 'Admin').
    """
    principal = {}   # Navbar Principal → {grupo: [itens]}
    secundaria = {}  # app → {navbar: [itens]}

    for item in qs:
        entrada = {'item': item, 'marcado': item.pk in habilitados}
        if item.app == 'intranet' and item.navbar == 'principal':
            if item.grupo == 'admin' and item.subgrupo:
                secao = f'Admin — {item.subgrupo.capitalize()}'
            elif item.grupo == 'grupos':
                secao = 'Grupos Gerais (Notícias, Bancos...)'
            elif item.grupo:
                secao = item.grupo.capitalize()
            else:
                secao = 'Outros'
            principal.setdefault(secao, []).append(entrada)
        else:
            app_label = item.get_app_display()
            nav_label = item.get_navbar_display()
            secundaria.setdefault(app_label, {}).setdefault(nav_label, []).append(entrada)

    # Navbar Principal sempre no topo, depois os apps secundários em ordem alfa
    arvore = {}
    if principal:
        arvore['🔷 Navbar Principal'] = principal
    for app_label in sorted(secundaria.keys()):
        arvore[app_label] = secundaria[app_label]
    return arvore


# ── MenuItem ─────────────────────────────────────────────────────────────────

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display  = ['label', 'app', 'navbar', 'ordem', 'ativo']
    list_filter   = ['app', 'navbar', 'ativo']
    list_editable = ['ordem', 'ativo']
    search_fields = ['label', 'url_name']
    ordering      = ['app', 'navbar', 'ordem']

    fieldsets = (
        (None, {
            'fields': ('app', 'navbar', 'label', 'url_name', 'icon', 'ordem', 'ativo'),
        }),
    )


# ── EmpresaMenuItem ──────────────────────────────────────────────────────────

@admin.register(EmpresaMenuItem)
class EmpresaMenuItemAdmin(admin.ModelAdmin):
    list_display  = ['empresa', 'menu_item', 'ativo']
    list_filter   = ['empresa', 'ativo', 'menu_item__app']
    list_editable = ['ativo']
    search_fields = ['empresa__razao_social', 'menu_item__label']

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('por-empresa/',
                 self.admin_site.admin_view(self.view_por_empresa),
                 name='menu_acesso_por_empresa'),
            path('por-empresa/<int:empresa_id>/',
                 self.admin_site.admin_view(self.view_por_empresa),
                 name='menu_acesso_por_empresa_id'),
        ]
        return custom + urls

    def view_por_empresa(self, request, empresa_id=None):
        from apps.incorporadora.models import Empresa
        empresas   = Empresa.objects.filter(ativo=True).order_by('razao_social')
        empresa_sel = get_object_or_404(Empresa, pk=empresa_id) if empresa_id else None

        if request.method == 'POST' and empresa_sel:
            ids_marcados = set(int(x) for x in request.POST.getlist('itens'))
            todos = MenuItem.objects.filter(ativo=True)
            for item in todos:
                if item.pk in ids_marcados:
                    EmpresaMenuItem.objects.get_or_create(empresa=empresa_sel, menu_item=item,
                                                          defaults={'ativo': True})
                else:
                    EmpresaMenuItem.objects.filter(empresa=empresa_sel, menu_item=item).delete()
            messages.success(request, f'Itens de "{empresa_sel}" atualizados.')
            return redirect(request.path)

        habilitados = set()
        if empresa_sel:
            habilitados = set(
                EmpresaMenuItem.objects.filter(empresa=empresa_sel, ativo=True)
                .values_list('menu_item_id', flat=True)
            )

        arvore = _build_arvore(
            MenuItem.objects.filter(ativo=True).order_by('app', 'navbar', 'ordem'),
            habilitados,
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Itens de Menu por Empresa',
            'empresas': empresas,
            'empresa_sel': empresa_sel,
            'arvore': arvore,
            'opts': self.model._meta,
        }
        return render(request, 'menu_acesso/admin_por_empresa.html', context)


# ── UsuarioEmpresa ───────────────────────────────────────────────────────────

@admin.register(UsuarioEmpresa)
class UsuarioEmpresaAdmin(admin.ModelAdmin):
    list_display      = ['user', 'empresa', 'qtd_itens']
    list_filter       = ['empresa']
    search_fields     = ['user__username', 'empresa__razao_social']
    filter_horizontal = ['itens']
    fieldsets = (
        (None, {
            'fields': ('user', 'empresa'),
        }),
        ('Itens habilitados', {
            'fields': ('itens',),
            'description': 'Itens que este usuário pode acessar (apenas os habilitados para a empresa aparecem aqui após o vínculo ser salvo).',
        }),
    )

    def qtd_itens(self, obj):
        return obj.itens.count()
    qtd_itens.short_description = 'Itens habilitados'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.empresa_id:
            empresa_item_ids = EmpresaMenuItem.objects.filter(
                empresa=obj.empresa, ativo=True
            ).values_list('menu_item_id', flat=True)
            form.base_fields['itens'].queryset = MenuItem.objects.filter(
                pk__in=empresa_item_ids
            )
        else:
            form.base_fields['itens'].queryset = MenuItem.objects.none()
        return form

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('por-usuario/',
                 self.admin_site.admin_view(self.view_por_usuario),
                 name='menu_acesso_por_usuario'),
            path('por-usuario/<int:ue_id>/',
                 self.admin_site.admin_view(self.view_por_usuario),
                 name='menu_acesso_por_usuario_id'),
        ]
        return custom + urls

    def view_por_usuario(self, request, ue_id=None):
        vinculos   = UsuarioEmpresa.objects.select_related('user', 'empresa').order_by('empresa', 'user__username')
        vinculo_sel = get_object_or_404(UsuarioEmpresa, pk=ue_id) if ue_id else None

        if request.method == 'POST' and vinculo_sel:
            ids_marcados = set(int(x) for x in request.POST.getlist('itens'))
            # Só permite itens que a empresa tem habilitados
            empresa_itens = set(
                EmpresaMenuItem.objects.filter(empresa=vinculo_sel.empresa, ativo=True)
                .values_list('menu_item_id', flat=True)
            )
            ids_validos = ids_marcados & empresa_itens
            vinculo_sel.itens.set(ids_validos)
            messages.success(request, f'Itens de "{vinculo_sel.user.username}" atualizados.')
            return redirect(request.path)

        habilitados = set()
        arvore      = {}
        if vinculo_sel:
            habilitados = set(vinculo_sel.itens.values_list('pk', flat=True))
            empresa_itens = set(
                EmpresaMenuItem.objects.filter(empresa=vinculo_sel.empresa, ativo=True)
                .values_list('menu_item_id', flat=True)
            )
            arvore = _build_arvore(
                MenuItem.objects.filter(pk__in=empresa_itens).order_by('app', 'navbar', 'ordem'),
                habilitados,
            )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Itens de Menu por Usuário',
            'vinculos': vinculos,
            'vinculo_sel': vinculo_sel,
            'arvore': arvore,
            'opts': self.model._meta,
        }
        return render(request, 'menu_acesso/admin_por_usuario.html', context)
