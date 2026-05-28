from django.contrib import admin
from .models import MinutaContrato


@admin.register(MinutaContrato)
class MinutaContratoAdmin(admin.ModelAdmin):
    list_display  = ('nome', 'tipo', 'ativo', 'alterado_em')
    list_filter   = ('tipo', 'ativo')
    search_fields = ('nome',)
