from django.db import migrations

ITENS = [
    ('Bliss Living - RI', 'bliss_cartorio', 'bi-file-earmark-text', 10),
    ('Cota 365 - RI', 'cota365:cartorio', 'bi-file-earmark-text', 20),
    ('Unidades Vendidas', 'cota365:vendas', 'bi-building-check', 30),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for label, url_name, icon, ordem in ITENS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', grupo='engenharia',
            url_name=url_name,
            defaults=dict(label=label, icon=icon, ordem=ordem, ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for _, url_name, _, _ in ITENS:
        MenuItem.objects.filter(
            app='intranet', navbar='principal', grupo='engenharia',
            url_name=url_name,
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0024_admin_assistente'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
