# apps/bliss/admin.py
from django.contrib import admin
from .models import Bliss

@admin.register(Bliss)
class BlissAdmin(admin.ModelAdmin):
    list_display = (
        "bloco", "unidade", "situacao", "tipologia",
        "area_privativa", "area_total", "perc_permuta",
        "garagem", "deposito",
        "valor_tabela_fmt", "valor_venda_fmt",
        "data_venda", "cliente", "email",
    )
    search_fields = (
        "unidade", "cliente", "email",
        "garagem", "deposito", "bloco",
        "tipologia", "situacao",
    )
    list_filter = (
        "situacao", "bloco", "tipologia",
        ("data_venda", admin.DateFieldListFilter),
    )
    ordering = ("bloco", "unidade")
    date_hierarchy = "data_venda"
    list_per_page = 50

    @admin.display(description="Valor tabela", ordering="valor_tabela")
    def valor_tabela_fmt(self, obj):
        return f"R$ {obj.valor_tabela:,.2f}"

    @admin.display(description="Valor venda", ordering="valor_venda")
    def valor_venda_fmt(self, obj):
        return f"R$ {obj.valor_venda:,.2f}"
