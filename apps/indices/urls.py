from django.urls import path
from . import views

app_name = 'indices'

urlpatterns = [
    # Indice
    path('', views.indice_list, name='indice_list'),
    path('novo/', views.indice_create, name='indice_create'),
    path('<int:pk>/editar/', views.indice_update, name='indice_update'),
    path('<int:pk>/excluir/', views.indice_delete, name='indice_delete'),

    # IndiceData
    path('valores/', views.indicedata_list, name='indicedata_list'),
    path('valores/novo/', views.indicedata_create, name='indicedata_create'),
    path('valores/<int:pk>/editar/', views.indicedata_update, name='indicedata_update'),
    path('valores/<int:pk>/excluir/', views.indicedata_delete, name='indicedata_delete'),
    path('valor/<int:indice_id>/<str:data_str>/', 
         views.buscar_indicedata_por_data,
         name='buscar_indicedata_por_data'),
    path('valor-sql/<int:indice_id>/<str:data_str>/', views.buscar_valor_sql, name='buscar_valor_sql'),
    path('pg/', views.fetch_postgres, name='fetch_postgres'),
    path('details/', views.indices_detail, name='indices_detail'),
    path('cubs_hoje/', views.cubs_hoje, name='cubs_hoje'),
]

# /indices/valor-sql/5/2025-09-21/
