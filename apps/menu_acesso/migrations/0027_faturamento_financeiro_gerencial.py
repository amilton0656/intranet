from django.db import migrations

ITENS = [
    dict(grupo='financeiro', subgrupo='faturamento', ordem=30),
    dict(grupo='gerencial', subgrupo='faturamento', ordem=90),
]


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for item in ITENS:
        MenuItem.objects.get_or_create(
            app='intranet', navbar='principal', grupo=item['grupo'],
            url_name='faturamento:resumo',
            defaults=dict(label='Faturamento', icon='bi-cash-coin',
                          subgrupo=item['subgrupo'], ordem=item['ordem'], ativo=True),
        )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='intranet', navbar='principal', grupo__in=['financeiro', 'gerencial'],
        url_name='faturamento:resumo',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0026_admin_faturamento'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
