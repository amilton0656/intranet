from django.db import migrations

ITENS = [
    dict(url_name='bliss_cartorio', label='Bliss Living - RI', ordem=1),
    dict(url_name='cota365:cartorio', label='Cota 365 - RI', ordem=2),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for item in ITENS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', grupo='financeiro',
            url_name=item['url_name'],
            defaults=dict(label=item['label'], icon='bi-file-earmark-text',
                          subgrupo='ri', ordem=item['ordem'], ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo='financeiro',
        url_name__in=[i['url_name'] for i in ITENS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0027_faturamento_financeiro_gerencial'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
