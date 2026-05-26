from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('incorporadora', '0003_unidade_tipo'),
    ]

    operations = [
        migrations.RenameField(
            model_name='unidade',
            old_name='codigo',
            new_name='numero',
        ),
    ]
