from django.contrib import admin
from .models import Empresa

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'cnpj', 'ativo')
    search_fields = ('razao_social', 'cnpj')
    list_filter = ('ativo',)
