from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='marketing',
        url_name='cota365:acessos',
        defaults=dict(label='Acessos de Clientes', icon='bi-person-check',
                      subgrupo='', ordem=10, ativo=True),
    )
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='marketing',
        url_name='clientes:lista',
        defaults=dict(label='Clientes', icon='bi-people',
                      subgrupo='', ordem=20, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='marketing',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0036_clientes_financeiro_admin'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
