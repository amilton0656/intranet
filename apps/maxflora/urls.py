from django.urls import path
from . import views

app_name = 'maxflora'

urlpatterns = [
    path('tabela/', views.tabela_vendas, name='tabela'),
]
