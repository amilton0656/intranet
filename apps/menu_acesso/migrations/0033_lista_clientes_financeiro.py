from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='financeiro',
        url_name='cota365:clientes',
        defaults=dict(label='Cota 365 — Lista de Clientes', icon='bi-people',
                      subgrupo='cota365', ordem=26, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='financeiro',
        url_name='cota365:clientes',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0032_lista_clientes_cota365'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
