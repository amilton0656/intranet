from django.db import migrations

ITENS = [
    # ── INTRANET — Navbar Principal ─────────────────────────────────────────
    # Financeiro
    ('intranet', 'principal', 'Bliss Living — Resumo',          'bliss_resumo',                   'bi-speedometer2',          10),
    ('intranet', 'principal', 'Bliss Living — Unidades',        'bliss_unidades_full',             'bi-building',              11),
    ('intranet', 'principal', 'Cota 365 — Resumo',              'cota365:dashboard',               'bi-speedometer2',          20),
    ('intranet', 'principal', 'Cota 365 — Unidades',            'cota365:unidades',                'bi-building',              21),
    ('intranet', 'principal', 'Cota 365 — Unidades Vendidas',   'cota365:vendas',                  'bi-list-check',            22),
    ('intranet', 'principal', 'Cota 365 — Fluxo Mensal',        'cota365:fluxo',                   'bi-bar-chart-line',        23),
    ('intranet', 'principal', 'Cota 365 — Parcelas',            'cota365:parcelas',                'bi-calendar-check',        24),
    ('intranet', 'principal', 'Cota 365 — Comissões',           'cota365:comissoes_cadastro',      'bi-percent',               25),
    # Admin / Incorporadora
    ('intranet', 'principal', 'Empresas',                       'incorporadora:empresa_list',      'bi-building',              30),
    ('intranet', 'principal', 'Empreendimentos',                'incorporadora:empreendimento_list','bi-buildings',            31),
    ('intranet', 'principal', 'Pessoas',                        'pessoas:pessoa_list',             'bi-people',                32),
    ('intranet', 'principal', 'Propostas',                      'propostas:proposta_list',         'bi-file-earmark-text',     33),
    ('intranet', 'principal', 'Contratos',                      'contratos:minuta_list',           'bi-file-earmark-ruled',    34),
    ('intranet', 'principal', 'Importar',                       'incorporadora:importar_redirect', 'bi-cloud-upload',          35),
    ('intranet', 'principal', 'Cartório',                       'cota365:cartorio',                'bi-journal-bookmark',      36),
    ('intranet', 'principal', 'Max & Flora — Tabela de Vendas', 'maxflora:tabela',                 'bi-shop',                  37),
    ('intranet', 'principal', 'Usuários',                       'usuario_list',                    'bi-people',                38),

    # ── BLISS — Navbar Secundária ────────────────────────────────────────────
    ('bliss', 'secundaria', 'Novo Registro',       'bliss_create',            'bi-plus-circle',       10),
    ('bliss', 'secundaria', 'Importar Excel',      'bliss_import',            'bi-file-earmark-excel',11),
    ('bliss', 'secundaria', 'Unidades',            'bliss_unidades_full',     'bi-building',          12),
    ('bliss', 'secundaria', 'Resumo',              'bliss_resumo',            'bi-speedometer2',      13),
    ('bliss', 'secundaria', 'Atualizar Situações', 'atualizar_situacoes',     'bi-arrow-repeat',      14),
    ('bliss', 'secundaria', 'Atualização Mensal',  'atualizacao_mensal',      'bi-calendar-month',    15),
    ('bliss', 'secundaria', 'Importar Clientes',   'bliss_import_clientes',   'bi-people',            16),

    # ── COTA 365 — Navbar Secundária ─────────────────────────────────────────
    ('cota365', 'secundaria', 'Resumo',             'cota365:dashboard',           'bi-speedometer2',      10),
    ('cota365', 'secundaria', 'Unidades',           'cota365:unidades',            'bi-building',          11),
    ('cota365', 'secundaria', 'Unidades Vendidas',  'cota365:vendas',              'bi-list-check',        12),
    ('cota365', 'secundaria', 'Fluxo Mensal',       'cota365:fluxo',               'bi-bar-chart-line',    13),
    ('cota365', 'secundaria', 'Parcelas',           'cota365:parcelas',            'bi-calendar-check',    14),
    ('cota365', 'secundaria', 'Comissões',          'cota365:comissoes_cadastro',  'bi-percent',           15),
    ('cota365', 'secundaria', 'Descontos',          'cota365:descontos',           'bi-arrow-left-right',  16),
    ('cota365', 'secundaria', 'Cartório',           'cota365:cartorio',            'bi-journal-bookmark',  17),
    ('cota365', 'secundaria', 'Importar',           'cota365:importar',            'bi-upload',            18),

    # ── ÍNDICES — Navbar Secundária ──────────────────────────────────────────
    ('indices', 'secundaria', 'Índices',    'indices:indice_list',       'bi-list-ul',       10),
    ('indices', 'secundaria', 'Novo Índice','indices:indice_create',     'bi-plus-circle',   11),
    ('indices', 'secundaria', 'Valores',    'indices:indicedata_list',   'bi-table',         12),
    ('indices', 'secundaria', 'Novo Valor', 'indices:indicedata_create', 'bi-plus-circle',   13),

    # ── CONTRATOS — Navbar Secundária ────────────────────────────────────────
    ('contratos', 'secundaria', 'Minutas',      'contratos:minuta_list',   'bi-file-earmark-ruled', 10),
    ('contratos', 'secundaria', 'Nova Minuta',  'contratos:minuta_create', 'bi-plus-circle',        11),
    ('contratos', 'secundaria', 'Variáveis',    'contratos:variaveis',     'bi-sliders',            12),

    # ── PROPOSTAS — Navbar Secundária ────────────────────────────────────────
    ('propostas', 'secundaria', 'Propostas',      'propostas:proposta_list',     'bi-file-earmark-text', 10),
    ('propostas', 'secundaria', 'Kanban',         'propostas:proposta_kanban',   'bi-kanban',            11),
    ('propostas', 'secundaria', 'Workflow',       'propostas:proposta_workflow', 'bi-diagram-3',         12),
    ('propostas', 'secundaria', 'Nova Proposta',  'propostas:proposta_create',   'bi-plus-circle',       13),

    # ── AJR PADRÃO — Navbar Secundária ──────────────────────────────────────
    ('ajr_padrao', 'secundaria', 'Resumo',            'cota365:dashboard',          'bi-speedometer2',     10),
    ('ajr_padrao', 'secundaria', 'Unidades',          'cota365:unidades',           'bi-building',         11),
    ('ajr_padrao', 'secundaria', 'Unidades Vendidas', 'cota365:vendas',             'bi-list-check',       12),
    ('ajr_padrao', 'secundaria', 'Fluxo Mensal',      'cota365:fluxo',              'bi-bar-chart-line',   13),
    ('ajr_padrao', 'secundaria', 'Parcelas',          'cota365:parcelas',           'bi-calendar-check',   14),
    ('ajr_padrao', 'secundaria', 'Comissões',         'cota365:comissoes_cadastro', 'bi-percent',          15),
    ('ajr_padrao', 'secundaria', 'Descontos',         'cota365:descontos',          'bi-arrow-left-right', 16),
    ('ajr_padrao', 'secundaria', 'Cartório',          'cota365:cartorio',           'bi-journal-bookmark', 17),
    ('ajr_padrao', 'secundaria', 'Importar',          'cota365:importar',           'bi-upload',           18),
]


def popular(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for app, navbar, label, url_name, icon, ordem in ITENS:
        MenuItem.objects.get_or_create(
            app=app, navbar=navbar, url_name=url_name,
            defaults=dict(label=label, icon=icon, ordem=ordem, ativo=True),
        )


def reverter(apps, schema_editor):
    # Remove apenas os itens criados por esta migration
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    url_names = [row[3] for row in ITENS]
    MenuItem.objects.filter(url_name__in=url_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menu_acesso', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(popular, reverter),
    ]
