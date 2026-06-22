from django.db import migrations


def aplicar(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.get_or_create(
        app='bliss', navbar='secundaria', url_name='bliss_cartorio',
        defaults=dict(
            label='Cartório',
            icon='bi-journal-bookmark',
            ordem=17,
            subgrupo='',
            ativo=True,
        ),
    )


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(
        app='bliss', navbar='secundaria', url_name='bliss_cartorio'
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0016_admin_bliss'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
