from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', grupo='admin',
        url_name='faturamento:resumo',
        defaults=dict(label='Faturamento', icon='bi-cash-coin', ordem=85, ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='admin',
        url_name='faturamento:resumo',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0025_engenharia_menu'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
