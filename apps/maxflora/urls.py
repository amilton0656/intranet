from django.urls import path
from . import views

app_name = 'maxflora'

urlpatterns = [
    path('tabela/',   views.tabela_vendas,  name='tabela'),
    path('importar/', views.importar_upload, name='importar'),
    path('pdf/',      views.exportar_pdf,    name='pdf'),
]
