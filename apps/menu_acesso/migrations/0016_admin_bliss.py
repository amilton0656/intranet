from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='admin', url_name='bliss_unidades',
        defaults=dict(label='Bliss Living', icon='bi-houses', ordem=65, subgrupo='', ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='admin', url_name='bliss_unidades'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0015_gerencial_descontos_link'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
