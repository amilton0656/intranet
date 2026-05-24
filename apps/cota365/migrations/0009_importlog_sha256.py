from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0008_add_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='importlog',
            name='sha256',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
