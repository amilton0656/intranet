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
    path('empreendimentos/<int:empreendimento_pk>/unidades/importar-csv/',      views.unidade_import_empreendimento_csv,   name='unidade_import_empreendimento_csv'),
    path('empreendimentos/<int:empreendimento_pk>/unidades/template-csv/',      views.unidade_csv_template_empreendimento, name='unidade_csv_template_empreendimento'),
    path('empreendimentos/<int:empreendimento_pk>/unidades/importar-tabela-cv/', views.unidade_import_tabela_cv,            name='unidade_import_tabela_cv'),
    path('empreendimentos/<int:empreendimento_pk>/vinculos/importar-csv/',      views.vinculos_import_empreendimento_csv,  name='vinculos_import_empreendimento_csv'),

    # Relatório completo por empreendimento
    path('empreendimentos/<int:pk>/relatorio/', views.empreendimento_relatorio_pdf, name='empreendimento_relatorio_pdf'),
    path('empreendimentos/<int:pk>/vinculos/pdf/', views.empreendimento_vinculos_pdf, name='empreendimento_vinculos_pdf'),
    path('empreendimentos/<int:pk>/resumo/',       views.empreendimento_resumo,       name='empreendimento_resumo'),
    path('empreendimentos/<int:pk>/resumo/pdf/',   views.empreendimento_resumo_pdf,   name='empreendimento_resumo_pdf'),
    path('empreendimentos/<int:pk>/resumo/email/', views.empreendimento_resumo_email, name='empreendimento_resumo_email'),
    path('empreendimentos/importar/',             views.importar_redirect,           name='importar_redirect'),
    path('empreendimentos/<int:pk>/importar/',    views.empreendimento_importar,     name='empreendimento_importar'),

    # Excel / CSV
    path('empreendimentos/exportar-excel/',          views.empreendimento_export_excel,    name='empreendimento_export_excel'),
    path('empreendimentos/<int:pk>/exportar-excel/', views.empreendimento_export_excel_pk, name='empreendimento_export_excel_pk'),
    path('empreendimentos/importar-csv/',     views.empreendimento_import_csv,   name='empreendimento_import_csv'),
    path('empreendimentos/template-csv/',     views.empreendimento_csv_template, name='empreendimento_csv_template'),

    # Tabela de Vendas
    path('empreendimentos/<int:empreendimento_pk>/tabelas/',       views.tabela_list,   name='tabela_list'),
    path('empreendimentos/<int:empreendimento_pk>/tabelas/nova/',  views.tabela_create, name='tabela_create'),
    path('tabelas/<int:pk>/',                                      views.tabela_detail, name='tabela_detail'),
    path('tabelas/<int:pk>/editar/',                               views.tabela_edit,   name='tabela_edit'),
    path('tabelas/<int:pk>/excluir/',                              views.tabela_delete, name='tabela_delete'),
    path('tabelas/<int:pk>/template-csv/',                         views.tabela_item_csv_template, name='tabela_item_csv_template'),
    path('tabelas/<int:pk>/importar-csv/',                         views.tabela_item_import_csv,   name='tabela_item_import_csv'),
    path('tabelas/<int:pk>/pdf/',                                  views.tabela_pdf,               name='tabela_pdf'),
    path('tabelas/<int:pk>/gerar-itens/',                          views.tabela_gerar_itens,        name='tabela_gerar_itens'),

    # Séries de Pagamento
    path('tabelas/<int:tabela_pk>/series/nova/', views.serie_create, name='serie_create'),
    path('series/<int:pk>/editar/',              views.serie_edit,   name='serie_edit'),
    path('series/<int:pk>/excluir/',             views.serie_delete, name='serie_delete'),

    # PDF exports
    path('empresas/pdf/',                                        views.empresa_list_pdf,       name='empresa_list_pdf'),
    path('empreendimentos/pdf/',                                 views.empreendimento_list_pdf, name='empreendimento_list_pdf'),
    path('empreendimentos/<int:empreendimento_pk>/blocos/pdf/',  views.bloco_list_pdf,         name='bloco_list_pdf'),
    path('blocos/<int:bloco_pk>/unidades/pdf/',                  views.unidade_list_pdf,       name='unidade_list_pdf'),
]
