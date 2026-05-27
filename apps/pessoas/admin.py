from django.contrib import admin
from .models import Pessoa


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'cpf_cnpj', 'celular', 'email', 'ativo')
    list_filter = ('tipo', 'ativo', 'is_cliente', 'is_corretor', 'is_imobiliaria', 'is_fornecedor')
    search_fields = ('nome', 'cpf_cnpj', 'email')
