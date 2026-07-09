from django.db import migrations

ITENS = [
    # subgrupo='bliss'
    ('Bliss - Resumo',         'bliss_resumo_pdf',         'bi-file-earmark-bar-graph', 'bliss',   10),
    ('Bliss - RI',             'bliss_cartorio',            'bi-journal-bookmark',       'bliss',   20),
    # subgrupo='cota365'
    ('Cota 365 - Resumo',      'cota365:export_dashboard',  'bi-file-earmark-bar-graph', 'cota365', 30),
    ('Cota 365 - Descontos',   'cota365:export_descontos',  'bi-arrow-left-right',       'cota365', 40),
    ('Cota 365 - RI',          'cota365:cartorio',          'bi-journal-bookmark',       'cota365', 50),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for label, url_name, icon, subgrupo, ordem in ITENS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', grupo='comercial',
            url_name=url_name,
            defaults=dict(label=label, icon=icon, subgrupo=subgrupo, ordem=ordem, ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for _, url_name, _, _, _ in ITENS:
        MenuItem.objects.filter(
            app='intranet', navbar='principal', grupo='comercial',
            url_name=url_name,
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0020_viabilidade_admin'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
