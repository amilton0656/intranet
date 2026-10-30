from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='financeiro',
        url_name='clientes:lista',
        defaults=dict(label='Clientes', icon='bi-people',
                      subgrupo='clientes', ordem=40, ativo=True),
    )
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='admin',
        url_name='clientes:lista',
        defaults=dict(label='Clientes', icon='bi-people',
                      subgrupo='', ordem=90, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo__in=['financeiro', 'admin'],
        url_name='clientes:lista',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0035_clientes_gerencial'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
