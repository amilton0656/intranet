from django.contrib import admin

from .models import SerieCondicao, ValorCondicaoUnidade


@admin.register(SerieCondicao)
class SerieCondicaoAdmin(admin.ModelAdmin):
    list_display = ('label', 'tipo', 'periodicidade', 'quantidade', 'primeiro_vencimento', 'ordem')
    list_filter = ('tipo',)


@admin.register(ValorCondicaoUnidade)
class ValorCondicaoUnidadeAdmin(admin.ModelAdmin):
    list_display = ('unidade', 'serie', 'valor_parcela')
    list_filter = ('serie',)
    search_fields = ('unidade',)
