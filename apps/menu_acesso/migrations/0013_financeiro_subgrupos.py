from django.db import migrations

BLISS = {'bliss_resumo', 'bliss_unidades_full'}


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    qs = MenuItem.objects.filter(app='intranet', navbar='principal', grupo='financeiro')
    for item in qs:
        item.subgrupo = 'bliss' if item.url_name in BLISS else 'cota365'
        item.save(update_fields=['subgrupo'])


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='financeiro'
    ).update(subgrupo='')


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0012_gerencial_subgrupos'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
