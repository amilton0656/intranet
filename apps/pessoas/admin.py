from django.contrib import admin
from .models import Pessoa


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display  = ('nome', 'tipo', 'cpf_cnpj', 'celular', 'email', 'ativo')
    list_filter   = ('tipo', 'ativo', 'is_cliente', 'is_corretor', 'is_imobiliaria', 'is_fornecedor')
    search_fields = ('nome', 'cpf_cnpj', 'email')
    fieldsets = (
        ('Identificação', {'fields': (
            'tipo', 'nome', 'cpf_cnpj', 'rg_ie', 'rg_orgao_emissor',
        )}),
        ('Pessoa Física', {'fields': (
            'nacionalidade', 'profissao', 'estado_civil', 'regime_bens',
        ), 'classes': ('collapse',)}),
        ('Pessoa Jurídica', {'fields': (
            'tipo_societario', 'representante',
        ), 'classes': ('collapse',)}),
        ('Contato', {'fields': (
            'email', 'telefone', 'celular',
        )}),
        ('Endereço', {'fields': (
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
        ), 'classes': ('collapse',)}),
        ('Dados Bancários', {'fields': (
            'banco_nome', 'banco_agencia', 'banco_conta', 'banco_tipo_conta',
        ), 'classes': ('collapse',)}),
        ('Papéis', {'fields': (
            'is_cliente', 'is_corretor', 'is_imobiliaria', 'is_fornecedor', 'is_outro',
        )}),
        ('Outros', {'fields': ('observacoes', 'ativo')}),
    )
