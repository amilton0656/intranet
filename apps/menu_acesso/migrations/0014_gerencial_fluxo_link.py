from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='cota365:export_fluxo',
    ).update(
        label='Cota 365 — Fluxo Mensal',
        url_name='cota365:fluxo',
        icon='bi-bar-chart-line',
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='gerencial',
        url_name='cota365:fluxo',
    ).update(
        label='Cota 365 — Fluxo Mensal (PDF)',
        url_name='cota365:export_fluxo',
        icon='bi-file-earmark-pdf',
    )


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0013_financeiro_subgrupos'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
