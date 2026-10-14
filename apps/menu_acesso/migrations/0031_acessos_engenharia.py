from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='engenharia',
        url_name='cota365:acessos',
        defaults=dict(label='Acessos de Clientes', icon='bi-person-check',
                      subgrupo='', ordem=40, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='engenharia',
        url_name='cota365:acessos',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0030_vpl_comercial'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
