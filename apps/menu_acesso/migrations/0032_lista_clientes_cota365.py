from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='cota365', navbar='secundaria',
        url_name='cota365:clientes',
        defaults=dict(label='Lista de Clientes', icon='bi-people', ordem=20, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='cota365', navbar='secundaria', url_name='cota365:clientes',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0031_acessos_engenharia'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
