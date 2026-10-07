from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='comercial',
        url_name='cota365:vpl_buscar',
        defaults=dict(label='Simular VPL', icon='bi-calculator',
                      subgrupo='cota365', ordem=60, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='comercial',
        url_name='cota365:vpl_buscar',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0029_vpl_gerencial'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
