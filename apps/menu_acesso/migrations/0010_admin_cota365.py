from django.db import migrations

NOVOS_ITENS = [
    ('Comissões',     'cota365:comissoes_cadastro', 'bi-percent',          10),
    ('Descontos',     'cota365:descontos',           'bi-arrow-left-right', 20),
    ('Cartório',      'cota365:cartorio',            'bi-journal-bookmark', 30),
    ('Importar',      'cota365:importar',            'bi-upload',           40),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')

    # remove cartório do subgrupo 'contratos' (era intranet/principal/admin)
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='admin',
        url_name='cota365:cartorio'
    ).delete()

    # cria todos os itens cota365 no admin
    for label, url_name, icon, ordem in NOVOS_ITENS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal',
            grupo='admin', subgrupo='cota365', url_name=url_name,
            defaults=dict(label=label, icon=icon, ordem=ordem, ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='admin', subgrupo='cota365'
    ).delete()
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='admin',
        url_name='cota365:cartorio',
        defaults=dict(label='Cartório', icon='bi-journal-bookmark',
                      ordem=36, subgrupo='contratos', ativo=True),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0009_ajr_padrao_grupo'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
