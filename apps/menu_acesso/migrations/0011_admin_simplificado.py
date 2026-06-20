from django.db import migrations

ITENS_ADMIN = [
    ('Cota 365',       'cota365:index',               'bi-building',           10),
    ('Incorporadora',  'incorporadora:empresa_list',   'bi-buildings',          20),
    ('Contratos',      'contratos:minuta_list',        'bi-file-earmark-ruled', 30),
    ('Propostas',      'propostas:proposta_list',      'bi-file-earmark-text',  40),
    ('Pessoas',        'pessoas:pessoa_list',          'bi-people',             50),
    ('Max & Flora',    'maxflora:tabela',              'bi-shop',               60),
    ('Usuários',       'usuario_list',                 'bi-person-gear',        70),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    # remove todos os itens admin existentes
    MenuItem.objects.filter(app='intranet', navbar='principal', grupo='admin').delete()
    # cria lista plana (sem subgrupo)
    for label, url_name, icon, ordem in ITENS_ADMIN:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', grupo='admin', url_name=url_name,
            defaults=dict(label=label, icon=icon, ordem=ordem, subgrupo='', ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(app='intranet', navbar='principal', grupo='admin').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0010_admin_cota365'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
