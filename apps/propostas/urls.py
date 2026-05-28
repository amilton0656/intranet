from django.urls import path
from . import views

app_name = 'propostas'

urlpatterns = [
    # Rotas fixas — devem vir ANTES de <str:numero>/
    path('',        views.proposta_list,     name='proposta_list'),
    path('pdf/',    views.proposta_list_pdf, name='proposta_list_pdf'),
    path('kanban/', views.proposta_kanban,   name='proposta_kanban'),
    path('nova/',   views.proposta_create,   name='proposta_create'),

    # Workflow
    path('workflow/',                    views.proposta_workflow, name='proposta_workflow'),
    path('workflow/salvar/',             views.workflow_salvar,   name='workflow_salvar'),
    path('workflow/etapa/criar/',        views.etapa_criar,       name='etapa_criar'),
    path('workflow/etapa/<slug:slug>/excluir/', views.etapa_excluir, name='etapa_excluir'),

    # Subrecursos sem número de proposta
    path('unidades/<int:pk>/remover/',       views.unidade_remove,     name='unidade_remove'),
    path('participantes/<int:pk>/remover/',  views.participante_remove, name='participante_remove'),
    path('series/<int:pk>/editar/',          views.serie_edit,          name='serie_edit'),
    path('series/<int:pk>/remover/',         views.serie_remove,        name='serie_remove'),
    path('documentos/<int:pk>/remover/',     views.documento_remove,    name='documento_remove'),

    # AJAX helpers
    path('tabelas/<int:tabela_pk>/unidades/', views.tabela_unidades_json, name='tabela_unidades_json'),
    path('kanban/mover/',                     views.kanban_mover,         name='kanban_mover'),

    # Rotas com <str:numero> — catch-all, devem vir por último
    path('<str:numero>/',                          views.proposta_detail,       name='proposta_detail'),
    path('<str:numero>/fluxo-pdf/',                views.proposta_fluxo_pdf,    name='proposta_fluxo_pdf'),
    path('<str:numero>/editar/',                   views.proposta_edit,         name='proposta_edit'),
    path('<str:numero>/excluir/',                  views.proposta_delete,       name='proposta_delete'),
    path('<str:numero>/unidades/adicionar/',        views.unidade_add,          name='unidade_add'),
    path('<str:numero>/participantes/adicionar/',   views.participante_add,     name='participante_add'),
    path('<str:numero>/series/adicionar/',          views.serie_add,            name='serie_add'),
    path('<str:numero>/series/copiar-tabela/',      views.series_copiar_tabela, name='series_copiar_tabela'),
    path('<str:numero>/documentos/upload/',         views.documento_upload,     name='documento_upload'),
]
