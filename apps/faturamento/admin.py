from django.contrib import admin
from .models import (
    Contrato, ImportacaoAReceber, ImportacaoFaturamento, ParcelaPendente, Recebimento,
)


@admin.register(ImportacaoFaturamento)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ('arquivo', 'importado_em', 'total_linhas')


@admin.register(Recebimento)
class RecebimentoAdmin(admin.ModelAdmin):
    list_display = ('data_baixa', 'nome_empresa', 'nome_cliente', 'categoria',
                     'nome_plano_financeiro', 'valor_liquido')
    list_filter = ('categoria', 'nome_empresa')
    search_fields = ('nome_cliente', 'numero_titulo', 'numero_unidade')


@admin.register(ImportacaoAReceber)
class ImportacaoAReceberAdmin(admin.ModelAdmin):
    list_display = ('arquivo', 'importado_em', 'total_linhas')


@admin.register(ParcelaPendente)
class ParcelaPendenteAdmin(admin.ModelAdmin):
    list_display = ('numero_titulo', 'numero_parcela', 'nome_empresa', 'nome_cliente',
                     'vencimento', 'valor_original', 'valor_saldo_atual')
    list_filter = ('nome_empresa',)
    search_fields = ('nome_cliente', 'numero_titulo', 'numero_unidade')


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ('numero_titulo', 'nome_empresa', 'nome_cliente', 'categoria',
                     'mes_venda', 'mes_venda_manual', 'valor_total')
    list_filter = ('categoria', 'nome_empresa')
    search_fields = ('numero_titulo', 'nome_cliente')
    list_editable = ('mes_venda_manual',)
