from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path
from django.contrib import messages
from django.utils.html import format_html
from .models import MenuItem


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display  = ['label', 'app', 'navbar', 'ordem', 'ativo', 'resumo_acesso']
    list_filter   = ['app', 'navbar', 'ativo']
    list_editable = ['ordem', 'ativo']
    search_fields = ['label', 'url_name']
    filter_horizontal = ['grupos', 'usuarios']
    ordering = ['app', 'navbar', 'ordem']

    fieldsets = (
        (None, {
            'fields': ('app', 'navbar', 'label', 'url_name', 'icon', 'ordem', 'ativo'),
        }),
        ('Controle de Acesso', {
            'fields': ('grupos', 'usuarios'),
            'description': 'Superusuários têm acesso a tudo automaticamente.',
        }),
    )

    def resumo_acesso(self, obj):
        grupos = ', '.join(obj.grupos.values_list('name', flat=True)) or '—'
        return format_html('<span title="Grupos: {}">{} grupo(s) · {} usuário(s)</span>',
                           grupos,
                           obj.grupos.count(),
                           obj.usuarios.count())
    resumo_acesso.short_description = 'Acesso'

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('por-grupo/', self.admin_site.admin_view(self.view_por_grupo),
                 name='menu_acesso_por_grupo'),
            path('por-grupo/<int:group_id>/', self.admin_site.admin_view(self.view_por_grupo),
                 name='menu_acesso_por_grupo_id'),
        ]
        return custom + urls

    def view_por_grupo(self, request, group_id=None):
        """Vista em árvore: seleciona grupo → marca/desmarca itens de menu."""
        grupos = Group.objects.order_by('name')
        grupo_sel = get_object_or_404(Group, pk=group_id) if group_id else None

        if request.method == 'POST' and grupo_sel:
            ids_marcados = set(int(x) for x in request.POST.getlist('itens'))
            todos = MenuItem.objects.filter(ativo=True)
            for item in todos:
                if item.pk in ids_marcados:
                    item.grupos.add(grupo_sel)
                else:
                    item.grupos.remove(grupo_sel)
            messages.success(request, f'Acessos do grupo "{grupo_sel.name}" atualizados.')
            return redirect(request.path)

        # Monta árvore agrupada por app > navbar
        arvore = {}
        itens = MenuItem.objects.filter(ativo=True).prefetch_related('grupos')
        for item in itens:
            app_label = item.get_app_display()
            nav_label = item.get_navbar_display()
            arvore.setdefault(app_label, {}).setdefault(nav_label, []).append({
                'item': item,
                'marcado': grupo_sel and item.grupos.filter(pk=grupo_sel.pk).exists(),
            })

        context = {
            **self.admin_site.each_context(request),
            'title': 'Acesso ao Menu por Grupo',
            'grupos': grupos,
            'grupo_sel': grupo_sel,
            'arvore': arvore,
            'opts': self.model._meta,
        }
        return render(request, 'menu_acesso/admin_por_grupo.html', context)
