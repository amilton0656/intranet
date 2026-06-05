import datetime
import django.db.models.deletion
from django.db import migrations, models


def set_competencia_atual(apps, schema_editor):
    Tabela = apps.get_model('cota365', 'Tabela')
    hoje = datetime.date.today()
    competencia = hoje.replace(day=1)
    Tabela.objects.filter(competencia__isnull=True).update(competencia=competencia)


class Migration(migrations.Migration):

    dependencies = [
        ('cota365', '0013_parcela_valor_original_alter_importlog_tipo_and_more'),
    ]

    operations = [
        # 1. adiciona competencia como nullable para compatibilidade com dados existentes
        migrations.AddField(
            model_name='tabela',
            name='competencia',
            field=models.DateField(null=True, blank=True),
        ),
        # 2. preenche registros existentes com o 1º dia do mês atual
        migrations.RunPython(set_competencia_atual, migrations.RunPython.noop),
        # 3. remove unique de unidade
        migrations.AlterField(
            model_name='tabela',
            name='unidade',
            field=models.CharField(max_length=50),
        ),
        # 4. torna competencia NOT NULL
        migrations.AlterField(
            model_name='tabela',
            name='competencia',
            field=models.DateField(),
        ),
        # 5. adiciona unique_together (unidade, competencia)
        migrations.AlterUniqueTogether(
            name='tabela',
            unique_together={('unidade', 'competencia')},
        ),
    ]
