from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0006_seriecontrato'),
    ]

    operations = [
        migrations.CreateModel(
            name='Parcela',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=20)),
                ('parcela', models.CharField(blank=True, max_length=30)),
                ('tipo', models.CharField(blank=True, max_length=10)),
                ('vencimento', models.DateField(blank=True, null=True)),
                ('data_pagamento', models.DateField(blank=True, null=True)),
                ('valor', models.FloatField(default=0)),
                ('cliente', models.CharField(blank=True, max_length=255)),
            ],
            options={
                'ordering': ['vencimento', 'titulo'],
            },
        ),
    ]
