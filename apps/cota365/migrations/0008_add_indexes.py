from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0007_parcela'),
    ]

    operations = [
        migrations.AlterField(
            model_name='importlog',
            name='tipo',
            field=models.CharField(choices=[('tabela', 'Tabela de Preços'), ('unidades', 'Unidades'), ('vendas', 'Vendas'), ('fluxo', 'Fluxo de Caixa'), ('vinculo', 'Vínculos'), ('permutas', 'Permutas'), ('series', 'Séries de Contratos')], db_index=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='parcela',
            name='vencimento',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='parcela',
            name='data_pagamento',
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name='comissao',
            name='beneficiario',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='comissao',
            name='imobiliaria',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
    ]
