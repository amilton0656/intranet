from django.contrib import admin

from .models import Cliente, ContratoLocacao, ContratoVenda, ImportLog


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'tipo_pessoa', 'tipo_cliente', 'telefone', 'email')
    list_filter = ('tipo_pessoa', 'tipo_cliente', 'situacao')
    search_fields = ('codigo', 'nome', 'cpf_cnpj', 'email')


@admin.register(ContratoVenda)
class ContratoVendaAdmin(admin.ModelAdmin):
    list_display = ('numero_contrato', 'cliente', 'nome_empreendimento', 'unidade', 'valor_total', 'situacao')
    list_filter = ('nome_empresa', 'situacao', 'tipo_venda')
    search_fields = ('numero_contrato', 'cliente__nome', 'unidade')


@admin.register(ContratoLocacao)
class ContratoLocacaoAdmin(admin.ModelAdmin):
    list_display = ('numero_contrato', 'cliente', 'nome_empreendimento', 'unidade', 'valor_contrato', 'situacao')
    list_filter = ('nome_empresa', 'situacao')
    search_fields = ('numero_contrato', 'cliente__nome', 'unidade')


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'importado_em', 'total_registros', 'nome_arquivo')
    list_filter = ('tipo',)
