from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0004_add_comissao_datas'),
    ]

    operations = [
        # Limpa dados incompatíveis com a nova estrutura
        migrations.RunSQL('DELETE FROM cota365_comissao;'),

        # Remove a constraint unique do numero
        migrations.AlterField(
            model_name='comissao',
            name='numero',
            field=models.CharField(max_length=20),
        ),

        # Remove campos que saíram do CSV
        migrations.RemoveField(model_name='comissao', name='situacao'),
        migrations.RemoveField(model_name='comissao', name='data_venda'),
        migrations.RemoveField(model_name='comissao', name='tipo_unidade'),
        migrations.RemoveField(model_name='comissao', name='pct_premio'),
        migrations.RemoveField(model_name='comissao', name='valor_premio'),

        # Novo campo
        migrations.AddField(
            model_name='comissao',
            name='beneficiario',
            field=models.CharField(max_length=255, blank=True),
        ),

        # Nova chave composta
        migrations.AlterUniqueTogether(
            name='comissao',
            unique_together={('numero', 'beneficiario', 'tipo_comissao')},
        ),
    ]
