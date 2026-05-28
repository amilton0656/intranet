from django.urls import path
from . import views

app_name = 'contratos'

urlpatterns = [
    path('',                          views.minuta_list,    name='minuta_list'),
    path('nova/',                     views.minuta_create,  name='minuta_create'),
    path('<int:pk>/editar/',          views.minuta_edit,    name='minuta_edit'),
    path('<int:pk>/excluir/',         views.minuta_delete,  name='minuta_delete'),
    path('gerar/<str:numero>/',       views.contrato_gerar, name='contrato_gerar'),
]
