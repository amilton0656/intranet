from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='cota365:export_descontos',
    ).update(
        label='Cota 365 — Descontos',
        url_name='cota365:descontos',
        icon='bi-arrow-left-right',
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='cota365:descontos',
    ).update(
        label='Cota 365 — Descontos (PDF)',
        url_name='cota365:export_descontos',
        icon='bi-file-earmark-pdf',
    )


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0014_gerencial_fluxo_link'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
