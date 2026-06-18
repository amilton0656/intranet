from django.contrib import admin
from .models import ImportacaoMaxFlora, UnidadeMaxFlora


class UnidadeInline(admin.TabularInline):
    model = UnidadeMaxFlora
    extra = 0
    readonly_fields = ('euc', 'espaco', 'locatario', 'situacao', 'area_total',
                       'valor_vendas', 'valor_aluguel', 'locado_ate')


@admin.register(ImportacaoMaxFlora)
class ImportacaoAdmin(admin.ModelAdmin):
    list_display = ('arquivo', 'importado_em', 'total_unidades')
    inlines = [UnidadeInline]


@admin.register(UnidadeMaxFlora)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ('euc', 'espaco', 'locatario', 'situacao', 'area_total',
                    'valor_vendas', 'valor_aluguel', 'locado_ate')
    list_filter = ('situacao',)
