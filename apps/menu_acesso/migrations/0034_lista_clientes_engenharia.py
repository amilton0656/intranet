from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='engenharia',
        url_name='cota365:clientes',
        defaults=dict(label='Lista de Clientes', icon='bi-people',
                      subgrupo='', ordem=50, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='engenharia',
        url_name='cota365:clientes',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0033_lista_clientes_financeiro'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
