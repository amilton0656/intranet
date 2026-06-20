from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='intranet', navbar='principal', url_name='grupo_ajr_padrao',
        defaults=dict(label='AJR Padrão', icon='bi-grid-1x2-fill',
                      ordem=1, grupo='grupos', ativo=True),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(app='intranet', navbar='principal',
                            url_name='grupo_ajr_padrao').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0008_grupos_navbar'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
