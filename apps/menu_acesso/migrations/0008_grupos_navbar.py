from django.db import migrations

GRUPOS = [
    ('Notícias',         'grupo_noticias',      'bi-newspaper',     5),
    ('Bancos',           'grupo_bancos',         'bi-bank2',        10),
    ('Órgãos Públicos',  'grupo_orgaos',         'bi-building-fill',15),
    ('Sites Úteis',      'grupo_sites_uteis',    'bi-globe',        20),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for label, url_name, icon, ordem in GRUPOS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', url_name=url_name,
            defaults=dict(label=label, icon=icon, ordem=ordem, grupo='grupos', ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(app='intranet', navbar='principal', grupo='grupos').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0007_gerencial_e_subgrupos'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
