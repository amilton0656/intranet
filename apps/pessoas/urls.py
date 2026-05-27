from django.urls import path
from . import views

app_name = 'pessoas'

urlpatterns = [
    path('',                    views.pessoa_list,     name='pessoa_list'),
    path('pdf/',                views.pessoa_list_pdf, name='pessoa_list_pdf'),
    path('nova/',               views.pessoa_create,   name='pessoa_create'),
    path('<int:pk>/editar/',    views.pessoa_edit,     name='pessoa_edit'),
    path('<int:pk>/excluir/',   views.pessoa_delete,   name='pessoa_delete'),
]
