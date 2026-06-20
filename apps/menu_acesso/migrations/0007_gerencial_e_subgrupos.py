from django.db import migrations

# subgrupos para itens já existentes no grupo 'admin'
ADMIN_SUBGRUPOS = {
    'incorporadora:empresa_list':       'incorporadora',
    'incorporadora:empreendimento_list':'incorporadora',
    'incorporadora:importar_redirect':  'incorporadora',
    'pessoas:pessoa_list':              'pessoas',
    'propostas:proposta_list':          'propostas',
    'contratos:minuta_list':            'contratos',
    'cota365:cartorio':                 'contratos',
    'maxflora:tabela':                  'maxflora',
    'usuario_list':                     'sistema',
}

# novos itens do Gerencial (migrados do hardcoded)
GERENCIAL = [
    ('Bliss Living — Resumo',        'bliss_resumo',           'bi-speedometer2',        10),
    ('Cota 365 — Resumo',            'cota365:dashboard',      'bi-speedometer2',        20),
    ('Cota 365 — Fluxo Mensal (PDF)','cota365:export_fluxo',   'bi-file-earmark-pdf',    30),
    ('Cota 365 — Descontos (PDF)',   'cota365:export_descontos','bi-file-earmark-pdf',   40),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')

    # 1. setar subgrupos nos itens admin existentes
    for url_name, subgrupo in ADMIN_SUBGRUPOS.items():
        MenuItem.objects.filter(app='intranet', navbar='principal',
                                grupo='admin', url_name=url_name).update(subgrupo=subgrupo)

    # 2. criar itens do Gerencial
    for label, url_name, icon, ordem in GERENCIAL:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', url_name=url_name, grupo='gerencial',
            defaults=dict(label=label, icon=icon, ordem=ordem, ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(app='intranet', navbar='principal',
                            grupo='admin').update(subgrupo='')
    MenuItem.objects.filter(app='intranet', navbar='principal',
                            grupo='gerencial').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0006_menuitem_subgrupo_alter_menuitem_grupo'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
