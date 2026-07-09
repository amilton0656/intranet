from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='grupos',
        url_name='grupo_tabelas_vendas',
        defaults=dict(label='Tabelas de Vendas', icon='bi-file-earmark-pdf', ordem=60, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='grupos',
        url_name='grupo_tabelas_vendas',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0021_comercial_menu'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
