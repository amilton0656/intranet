from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='bliss_resumo',
    ).update(subgrupo='bliss')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
    ).exclude(url_name='bliss_resumo').update(subgrupo='cota365')


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
    ).update(subgrupo='')


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0011_admin_simplificado'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
