from django.urls import path
from . import views

app_name = 'incorporadora'

urlpatterns = [
    # Empresa
    path('empresas/',                          views.empresa_list,           name='empresa_list'),
    path('empresas/novo/',                     views.empresa_create,         name='empresa_create'),
    path('empresas/<int:pk>/editar/',          views.empresa_edit,           name='empresa_edit'),
    path('empresas/<int:pk>/excluir/',         views.empresa_delete,         name='empresa_delete'),

    # Empreendimento
    path('empreendimentos/',                   views.empreendimento_list,    name='empreendimento_list'),
    path('empreendimentos/novo/',              views.empreendimento_create,  name='empreendimento_create'),
    path('empreendimentos/<int:pk>/editar/',   views.empreendimento_edit,    name='empreendimento_edit'),
    path('empreendimentos/<int:pk>/excluir/',  views.empreendimento_delete,  name='empreendimento_delete'),

    # Bloco (sempre no contexto de um empreendimento)
    path('empreendimentos/<int:empreendimento_pk>/blocos/',        views.bloco_list,   name='bloco_list'),
    path('empreendimentos/<int:empreendimento_pk>/blocos/novo/',   views.bloco_create, name='bloco_create'),
    path('blocos/<int:pk>/editar/',                                views.bloco_edit,   name='bloco_edit'),
    path('blocos/<int:pk>/excluir/',                               views.bloco_delete, name='bloco_delete'),

    # Vínculos
    path('blocos/<int:bloco_pk>/vinculos/',             views.vinculo_list,         name='vinculo_list'),
    path('blocos/<int:bloco_pk>/vinculos/importar-csv/', views.vinculo_import_csv,  name='vinculo_import_csv'),
    path('blocos/<int:bloco_pk>/vinculos/template-csv/', views.vinculo_csv_template, name='vinculo_csv_template'),

    # Unidade (sempre no contexto de um bloco)
    path('blocos/<int:bloco_pk>/unidades/',                    views.unidade_list,           name='unidade_list'),
    path('blocos/<int:bloco_pk>/unidades/nova/',               views.unidade_create,         name='unidade_create'),
    path('blocos/<int:bloco_pk>/unidades/exportar-excel/',     views.unidade_export_excel,   name='unidade_export_excel'),
    path('blocos/<int:bloco_pk>/unidades/importar-csv/',       views.unidade_import_csv,     name='unidade_import_csv'),
    path('blocos/<int:bloco_pk>/unidades/template-csv/',       views.unidade_csv_template,   name='unidade_csv_template'),
    path('unidades/<int:pk>/editar/',                          views.unidade_edit,           name='unidade_edit'),
    path('unidades/<int:pk>/excluir/',                         views.unidade_delete,         name='unidade_delete'),

    # Importação de unidades no nível do empreendimento
    path('empreendimentos/<int:empreendimento_pk>/unidades/importar-csv/', views.unidade_import_empreendimento_csv,   name='unidade_import_empreendimento_csv'),
    path('empreendimentos/<int:empreendimento_pk>/unidades/template-csv/', views.unidade_csv_template_empreendimento, name='unidade_csv_template_empreendimento'),

    # Relatório completo por empreendimento
    path('empreendimentos/<int:pk>/relatorio/', views.empreendimento_relatorio_pdf, name='empreendimento_relatorio_pdf'),

    # Excel / CSV
    path('empreendimentos/exportar-excel/',   views.empreendimento_export_excel, name='empreendimento_export_excel'),
    path('empreendimentos/importar-csv/',     views.empreendimento_import_csv,   name='empreendimento_import_csv'),
    path('empreendimentos/template-csv/',     views.empreendimento_csv_template, name='empreendimento_csv_template'),

    # PDF exports
    path('empresas/pdf/',                                        views.empresa_list_pdf,       name='empresa_list_pdf'),
    path('empreendimentos/pdf/',                                 views.empreendimento_list_pdf, name='empreendimento_list_pdf'),
    path('empreendimentos/<int:empreendimento_pk>/blocos/pdf/',  views.bloco_list_pdf,         name='bloco_list_pdf'),
    path('blocos/<int:bloco_pk>/unidades/pdf/',                  views.unidade_list_pdf,       name='unidade_list_pdf'),
]
