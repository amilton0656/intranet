# from django.contrib import admin
from django.urls import path
# from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.tab_bliss, name="tab_bliss"),
    path('novo/', views.bliss_create, name='bliss_create'),
    path('editar/<int:pk>/', views.bliss_update, name='bliss_update'),
    path('excluir/<int:pk>/', views.bliss_delete, name='bliss_delete'),
    path('relatorio/', views.bliss_report, name='bliss_report'),
    path('relatorio/pdf/', views.bliss_pdf_report, name='bliss_pdf_report'),
    path('resumo/', views.bliss_summary, name='bliss_summary'),
    path('atualizar-situacoes/', views.atualizar_situacoes, name='atualizar_situacoes'),
    path('importar/', views.bliss_import, name='bliss_import'),
    path('atualizacao_mensal/', views.atualizacao_mensal, name='atualizacao_mensal'),
]
