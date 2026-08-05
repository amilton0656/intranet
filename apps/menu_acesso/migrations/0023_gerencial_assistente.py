from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='assistente:pesquisa',
        defaults=dict(label='Assistente IA', icon='bi-robot', ordem=5,
                      subgrupo='assistente', ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='assistente:pesquisa',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0022_tabelas_vendas_grupo'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
