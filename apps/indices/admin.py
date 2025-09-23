# apps/indices/admin.py
from django.contrib import admin
from .models import Indice, IndiceData

@admin.register(Indice)
class IndiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'descricao', 'periodo', 'calculo', 'tipo', 'created_at')
    list_filter = ('periodo', 'calculo', 'tipo')
    search_fields = ('descricao',)
    ordering = ('descricao',)

@admin.register(IndiceData)
class IndiceDataAdmin(admin.ModelAdmin):
    list_display = ('indice', 'data', 'valor', 'created_at')
    list_filter = ('indice',)
    date_hierarchy = 'data'
    search_fields = ('indice__descricao',)
    ordering = ('-data',)
