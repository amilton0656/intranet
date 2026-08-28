from django.urls import path
from . import views, views_anual

app_name = 'faturamento'

urlpatterns = [
    # Análise Anual é a página inicial do app.
    path('', views_anual.resumo, name='resumo'),
    path('anual/', views_anual.resumo, name='anual_resumo'),
    path('anual/mes/<int:ano>/<int:mes>/', views_anual.detalhe_mes_geral, name='anual_detalhe_geral'),
    path('anual/<str:codigo_empresa>/', views_anual.fluxo_empresa, name='anual_empresa'),
    path('anual/<str:codigo_empresa>/<int:ano>/<int:mes>/', views_anual.detalhe_mes, name='anual_detalhe'),

    # Resumo detalhado (com filtros, PDF) — antiga página inicial.
    path('detalhado/', views.resumo, name='detalhado'),
    path('detalhado/pdf/', views.exportar_pdf, name='pdf'),
]
