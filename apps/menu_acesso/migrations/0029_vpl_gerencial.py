from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='cota365:vpl_buscar',
        defaults=dict(label='Simular VPL', icon='bi-calculator',
                      subgrupo='cota365', ordem=100, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='cota365:vpl_buscar',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0028_ri_financeiro'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
