from django.contrib import admin
from .models import ImportacaoFaturamento, Recebimento


@admin.register(ImportacaoFaturamento)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ('arquivo', 'importado_em', 'total_linhas')


@admin.register(Recebimento)
class RecebimentoAdmin(admin.ModelAdmin):
    list_display = ('data_baixa', 'nome_empresa', 'nome_cliente', 'categoria',
                     'nome_plano_financeiro', 'valor_liquido')
    list_filter = ('categoria', 'nome_empresa')
    search_fields = ('nome_cliente', 'numero_titulo', 'numero_unidade')
