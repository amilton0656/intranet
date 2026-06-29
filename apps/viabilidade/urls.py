from django.urls import path
from . import views
from . import views_painel as vp

app_name = 'viabilidade'

urlpatterns = [
    # ---- Painel principal (interface única com abas) ----
    path('estudos/<int:pk>/painel/', vp.EstudoPainelView.as_view(), name='estudo_painel'),
    path('estudos/<int:pk>/calcular/', vp.estudo_calcular_ajax, name='estudo_calcular'),
    path('estudos/<int:pk>/resultado/', views.exportar_resultado,   name='estudo_resultado'),
    path('estudos/<int:pk>/fluxo/',    views.exportar_fluxo_caixa, name='estudo_fluxo'),

    # HTMX — Config
    path('htmx/<int:estudo_pk>/config/', vp.htmx_config_table, name='htmx_config_table'),
    path('htmx/<int:estudo_pk>/config/form/', vp.htmx_config_form, name='htmx_config_form_new'),
    path('htmx/<int:estudo_pk>/config/<int:pk>/form/', vp.htmx_config_form, name='htmx_config_form_edit'),
    path('htmx/<int:estudo_pk>/config/save/', vp.htmx_config_save, name='htmx_config_save_new'),
    path('htmx/<int:estudo_pk>/config/<int:pk>/save/', vp.htmx_config_save, name='htmx_config_save_edit'),
    path('htmx/<int:estudo_pk>/config/<int:pk>/delete/', vp.htmx_config_delete, name='htmx_config_delete'),

    # HTMX — Velocidade
    path('htmx/<int:estudo_pk>/veloc/', vp.htmx_veloc_table, name='htmx_veloc_table'),
    path('htmx/<int:estudo_pk>/veloc/form/', vp.htmx_veloc_form, name='htmx_veloc_form_new'),
    path('htmx/<int:estudo_pk>/veloc/<int:pk>/form/', vp.htmx_veloc_form, name='htmx_veloc_form_edit'),
    path('htmx/<int:estudo_pk>/veloc/save/', vp.htmx_veloc_save, name='htmx_veloc_save_new'),
    path('htmx/<int:estudo_pk>/veloc/<int:pk>/save/', vp.htmx_veloc_save, name='htmx_veloc_save_edit'),
    path('htmx/<int:estudo_pk>/veloc/<int:pk>/delete/', vp.htmx_veloc_delete, name='htmx_veloc_delete'),

    # HTMX — Construção
    path('htmx/<int:estudo_pk>/constru/', vp.htmx_constru_table, name='htmx_constru_table'),
    path('htmx/<int:estudo_pk>/constru/form/', vp.htmx_constru_form, name='htmx_constru_form_new'),
    path('htmx/<int:estudo_pk>/constru/<int:pk>/form/', vp.htmx_constru_form, name='htmx_constru_form_edit'),
    path('htmx/<int:estudo_pk>/constru/save/', vp.htmx_constru_save, name='htmx_constru_save_new'),
    path('htmx/<int:estudo_pk>/constru/<int:pk>/save/', vp.htmx_constru_save, name='htmx_constru_save_edit'),
    path('htmx/<int:estudo_pk>/constru/<int:pk>/delete/', vp.htmx_constru_delete, name='htmx_constru_delete'),

    # HTMX — Distribuição
    path('htmx/<int:estudo_pk>/distrib/', vp.htmx_distrib_table, name='htmx_distrib_table'),
    path('htmx/<int:estudo_pk>/distrib/form/', vp.htmx_distrib_form, name='htmx_distrib_form_new'),
    path('htmx/<int:estudo_pk>/distrib/<int:pk>/form/', vp.htmx_distrib_form, name='htmx_distrib_form_edit'),
    path('htmx/<int:estudo_pk>/distrib/save/', vp.htmx_distrib_save, name='htmx_distrib_save_new'),
    path('htmx/<int:estudo_pk>/distrib/<int:pk>/save/', vp.htmx_distrib_save, name='htmx_distrib_save_edit'),
    path('htmx/<int:estudo_pk>/distrib/<int:pk>/delete/', vp.htmx_distrib_delete, name='htmx_distrib_delete'),

    # HTMX — Parâmetros de Venda
    path('htmx/<int:estudo_pk>/param/', vp.htmx_param_table, name='htmx_param_table'),
    path('htmx/<int:estudo_pk>/param/form/', vp.htmx_param_form, name='htmx_param_form_new'),
    path('htmx/<int:estudo_pk>/param/<int:pk>/form/', vp.htmx_param_form, name='htmx_param_form_edit'),
    path('htmx/<int:estudo_pk>/param/save/', vp.htmx_param_save, name='htmx_param_save_new'),
    path('htmx/<int:estudo_pk>/param/<int:pk>/save/', vp.htmx_param_save, name='htmx_param_save_edit'),
    path('htmx/<int:estudo_pk>/param/<int:pk>/delete/', vp.htmx_param_delete, name='htmx_param_delete'),

    # HTMX — Agrupamentos
    path('htmx/<int:estudo_pk>/agrup/', vp.htmx_agrup_table, name='htmx_agrup_table'),
    path('htmx/<int:estudo_pk>/agrup/form/', vp.htmx_agrup_form, name='htmx_agrup_form_new'),
    path('htmx/<int:estudo_pk>/agrup/<int:pk>/form/', vp.htmx_agrup_form, name='htmx_agrup_form_edit'),
    path('htmx/<int:estudo_pk>/agrup/save/', vp.htmx_agrup_save, name='htmx_agrup_save_new'),
    path('htmx/<int:estudo_pk>/agrup/<int:pk>/save/', vp.htmx_agrup_save, name='htmx_agrup_save_edit'),
    path('htmx/<int:estudo_pk>/agrup/<int:pk>/delete/', vp.htmx_agrup_delete, name='htmx_agrup_delete'),

    # HTMX — Custos (catálogo global)
    path('htmx/custos/', vp.htmx_custo_modal, name='htmx_custo_modal'),
    path('htmx/custos/save/', vp.htmx_custo_save, name='htmx_custo_save'),
    path('htmx/custos/<int:pk>/delete/', vp.htmx_custo_delete, name='htmx_custo_delete'),

    # HTMX — Curvas (catálogo global)
    path('htmx/curvas/', vp.htmx_curva_modal, name='htmx_curva_modal'),
    path('htmx/curvas/save/', vp.htmx_curva_save, name='htmx_curva_save_new'),
    path('htmx/curvas/<int:pk>/delete/', vp.htmx_curva_delete, name='htmx_curva_delete'),
    path('htmx/curvas/<int:curva_pk>/meses/', vp.htmx_curva_meses, name='htmx_curva_meses'),
    path('htmx/curvas/<int:curva_pk>/meses/save/', vp.htmx_curvames_save, name='htmx_curvames_save'),
    path('htmx/curvas/<int:curva_pk>/meses/<int:pk>/delete/', vp.htmx_curvames_delete, name='htmx_curvames_delete'),

    # HTMX — Tipos (catálogo global)
    path('htmx/tipos/', vp.htmx_tipo_modal, name='htmx_tipo_modal'),
    path('htmx/tipos/form/', vp.htmx_tipo_form, name='htmx_tipo_form_new'),
    path('htmx/tipos/<int:pk>/form/', vp.htmx_tipo_form, name='htmx_tipo_form_edit'),
    path('htmx/tipos/save/', vp.htmx_tipo_save, name='htmx_tipo_save_new'),
    path('htmx/tipos/<int:pk>/save/', vp.htmx_tipo_save, name='htmx_tipo_save_edit'),
    path('htmx/tipos/<int:pk>/delete/', vp.htmx_tipo_delete, name='htmx_tipo_delete'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Empreendimentos
    path('empreendimentos/', views.EmpreendimentoListView.as_view(), name='empreendimento_list'),
    path('empreendimentos/novo/', views.EmpreendimentoCreateView.as_view(), name='empreendimento_create'),
    path('empreendimentos/<int:pk>/editar/', views.EmpreendimentoUpdateView.as_view(), name='empreendimento_update'),
    path('empreendimentos/<int:pk>/excluir/', views.EmpreendimentoDeleteView.as_view(), name='empreendimento_delete'),

    # Estudos
    path('estudos/', views.EstudoListView.as_view(), name='estudo_list'),
    path('estudos/novo/', views.EstudoCreateView.as_view(), name='estudo_create'),
    path('estudos/<int:pk>/', views.EstudoDetailView.as_view(), name='estudo_detail'),
    path('estudos/<int:pk>/editar/', views.EstudoUpdateView.as_view(), name='estudo_update'),
    path('estudos/<int:pk>/excluir/', views.EstudoDeleteView.as_view(), name='estudo_delete'),

    # Resultado / Fluxo
    path('estudos/<int:pk>/resultado/', views.EstudoResultadoView.as_view(), name='estudo_resultado'),
    path('estudos/<int:pk>/fluxo/', views.EstudoFluxoView.as_view(), name='estudo_fluxo'),

    # Configurações de Unidades
    path('estudos/<int:estudo_pk>/configs/', views.ConfigListView.as_view(), name='config_list'),
    path('estudos/<int:estudo_pk>/configs/novo/', views.ConfigCreateView.as_view(), name='config_create'),
    path('estudos/<int:estudo_pk>/configs/<int:pk>/editar/', views.ConfigUpdateView.as_view(), name='config_update'),
    path('estudos/<int:estudo_pk>/configs/<int:pk>/excluir/', views.ConfigDeleteView.as_view(), name='config_delete'),

    # Velocidade de Vendas
    path('estudos/<int:estudo_pk>/velocidades/', views.VelocidadeListView.as_view(), name='velocidade_list'),
    path('estudos/<int:estudo_pk>/velocidades/novo/', views.VelocidadeCreateView.as_view(), name='velocidade_create'),
    path('estudos/<int:estudo_pk>/velocidades/<int:pk>/editar/', views.VelocidadeUpdateView.as_view(), name='velocidade_update'),
    path('estudos/<int:estudo_pk>/velocidades/<int:pk>/excluir/', views.VelocidadeDeleteView.as_view(), name='velocidade_delete'),

    # Construção
    path('estudos/<int:estudo_pk>/construcoes/', views.ConstrucaoListView.as_view(), name='construcao_list'),
    path('estudos/<int:estudo_pk>/construcoes/novo/', views.ConstrucaoCreateView.as_view(), name='construcao_create'),
    path('estudos/<int:estudo_pk>/construcoes/<int:pk>/editar/', views.ConstrucaoUpdateView.as_view(), name='construcao_update'),
    path('estudos/<int:estudo_pk>/construcoes/<int:pk>/excluir/', views.ConstrucaoDeleteView.as_view(), name='construcao_delete'),

    # Parâmetros de Venda
    path('estudos/<int:estudo_pk>/params-vendas/', views.ParamVendasListView.as_view(), name='paramvendas_list'),
    path('estudos/<int:estudo_pk>/params-vendas/novo/', views.ParamVendasCreateView.as_view(), name='paramvendas_create'),
    path('estudos/<int:estudo_pk>/params-vendas/<int:pk>/editar/', views.ParamVendasUpdateView.as_view(), name='paramvendas_update'),
    path('estudos/<int:estudo_pk>/params-vendas/<int:pk>/excluir/', views.ParamVendasDeleteView.as_view(), name='paramvendas_delete'),

    # Curvas
    path('curvas/', views.CurvaListView.as_view(), name='curva_list'),
    path('curvas/novo/', views.CurvaCreateView.as_view(), name='curva_create'),
    path('curvas/<int:pk>/editar/', views.CurvaUpdateView.as_view(), name='curva_update'),
    path('curvas/<int:pk>/excluir/', views.CurvaDeleteView.as_view(), name='curva_delete'),
    path('curvas/<int:curva_pk>/meses/', views.CurvaMesListView.as_view(), name='curvames_list'),
    path('curvas/<int:curva_pk>/meses/novo/', views.CurvaMesCreateView.as_view(), name='curvames_create'),
    path('curvas/<int:curva_pk>/meses/<int:pk>/editar/', views.CurvaMesUpdateView.as_view(), name='curvames_update'),
    path('curvas/<int:curva_pk>/meses/<int:pk>/excluir/', views.CurvaMesDeleteView.as_view(), name='curvames_delete'),

    # Tipos
    path('tipos/', views.TipoListView.as_view(), name='tipo_list'),
    path('tipos/novo/', views.TipoCreateView.as_view(), name='tipo_create'),
    path('tipos/<int:pk>/editar/', views.TipoUpdateView.as_view(), name='tipo_update'),
    path('tipos/<int:pk>/excluir/', views.TipoDeleteView.as_view(), name='tipo_delete'),
]
