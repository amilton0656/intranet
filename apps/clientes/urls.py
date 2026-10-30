from django.urls import path

from . import views

app_name = 'clientes'

urlpatterns = [
    path('', views.lista, name='lista'),
    path('export/', views.exportar, name='exportar'),
    path('importar/', views.importar, name='importar'),
    path('<str:codigo>/', views.detalhe, name='detalhe'),
]
