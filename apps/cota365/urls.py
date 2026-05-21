from django.urls import path
from . import views

app_name = 'cota365'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('vendas/', views.vendas, name='vendas'),
    path('fluxo/', views.fluxo_mensal, name='fluxo'),
    path('dashboard/export/', views.export_dashboard, name='export_dashboard'),
    path('unidades/', views.unidades, name='unidades'),
    path('unidades/export/', views.export_unidades, name='export_unidades'),
    path('vendas/export/', views.export_vendas, name='export_vendas'),
    path('fluxo/export/', views.export_fluxo, name='export_fluxo'),
    path('comissoes/', views.comissoes, name='comissoes'),
    path('comissoes/export/pdf/', views.export_comissoes_pdf, name='export_comissoes_pdf'),
    path('comissoes/export/excel/', views.export_comissoes_excel, name='export_comissoes_excel'),
    path('importar/', views.importar, name='importar'),
    path('areas/comparativo/', views.export_areas_comparativo, name='export_areas_comparativo'),
]
