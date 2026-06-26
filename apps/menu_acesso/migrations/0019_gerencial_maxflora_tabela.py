from django.db import migrations

NOVOS_ITENS = [
    ('Tabela Max & Flora', 'maxflora:tabela', 'bi-table', 'maxflora', 10),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for label, url_name, icon, subgrupo, ordem in NOVOS_ITENS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', grupo='gerencial',
            url_name=url_name,
            defaults=dict(label=label, icon=icon, ordem=ordem,
                          subgrupo=subgrupo, ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for _, url_name, _, _, _ in NOVOS_ITENS:
        MenuItem.objects.filter(
            app='intranet', navbar='principal', grupo='gerencial',
            url_name=url_name,
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0018_gerencial_ri_links'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
