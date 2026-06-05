from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0014_tabela_competencia'),
    ]

    operations = [
        migrations.AddField(
            model_name='venda',
            name='valor_contrato',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='venda',
            name='data_venda',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
    ]
