from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0005_comissao_reestrutura'),
    ]

    operations = [
        migrations.CreateModel(
            name='SerieContrato',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('serie', models.CharField(max_length=100)),
                ('reserva', models.CharField(max_length=20)),
                ('total_sem_comissao', models.FloatField(default=0)),
                ('total', models.FloatField(default=0)),
            ],
            options={
                'ordering': ['reserva', 'serie'],
            },
        ),
    ]
