from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='admin',
        url_name='assistente:pesquisa',
        defaults=dict(label='Assistente IA', icon='bi-robot', ordem=45, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='admin',
        url_name='assistente:pesquisa',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0023_gerencial_assistente'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
