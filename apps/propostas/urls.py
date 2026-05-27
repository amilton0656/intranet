from django.urls import path
from . import views

app_name = 'propostas'

urlpatterns = [
    path('',                          views.proposta_list,   name='proposta_list'),
    path('nova/',                     views.proposta_create, name='proposta_create'),
    path('<str:numero>/',             views.proposta_detail, name='proposta_detail'),
    path('<str:numero>/editar/',      views.proposta_edit,   name='proposta_edit'),
    path('<str:numero>/excluir/',     views.proposta_delete, name='proposta_delete'),

    # Unidades
    path('<str:numero>/unidades/adicionar/', views.unidade_add,    name='unidade_add'),
    path('unidades/<int:pk>/remover/',       views.unidade_remove, name='unidade_remove'),

    # Participantes
    path('<str:numero>/participantes/adicionar/', views.participante_add,    name='participante_add'),
    path('participantes/<int:pk>/remover/',       views.participante_remove, name='participante_remove'),

    # Séries
    path('<str:numero>/series/adicionar/',  views.serie_add,    name='serie_add'),
    path('series/<int:pk>/editar/',         views.serie_edit,   name='serie_edit'),
    path('series/<int:pk>/remover/',        views.serie_remove, name='serie_remove'),
    path('<str:numero>/series/copiar-tabela/', views.series_copiar_tabela, name='series_copiar_tabela'),

    # Documentos
    path('<str:numero>/documentos/upload/', views.documento_upload, name='documento_upload'),
    path('documentos/<int:pk>/remover/',    views.documento_remove, name='documento_remove'),

    # AJAX helpers
    path('tabelas/<int:tabela_pk>/unidades/', views.tabela_unidades_json, name='tabela_unidades_json'),
]
