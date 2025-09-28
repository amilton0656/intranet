# from django.contrib import admin
from django.urls import path
# from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.bliss_unidades, name="bliss_unidades"),
    path('novo/', views.bliss_create, name='bliss_create'),
    path('editar/<int:pk>/', views.bliss_update, name='bliss_update'),
    path('excluir/<int:pk>/', views.bliss_delete, name='bliss_delete'),
    path('bliss_unidades_full/', views.bliss_unidades_full, name='bliss_unidades_full'),
    path('bliss_unidades_full/pdf/', views.bliss_unidades_full_pdf, name='bliss_unidades_full_pdf'),
    path('atualizar-situacoes/', views.atualizar_situacoes, name='atualizar_situacoes'),
    path('importar/', views.bliss_import, name='bliss_import'),
    path('atualizacao_mensal/', views.atualizacao_mensal, name='atualizacao_mensal'),
    path('bliss_resumo', views.bliss_resumo, name='bliss_resumo'),
    path('resumo2/', views.bliss_summary, name='bliss_summary'),
]
