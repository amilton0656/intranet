from django.urls import path
from . import views

app_name = 'faturamento'

urlpatterns = [
    path('', views.resumo, name='resumo'),
    path('pdf/', views.exportar_pdf, name='pdf'),
]
