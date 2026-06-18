from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maxflora', '0001_initial'),
    ]

    operations = [
        # Renomeia euc → loja
        migrations.RenameField(
            model_name='unidademaxflora',
            old_name='euc',
            new_name='loja',
        ),
        # Remove espaco
        migrations.RemoveField(
            model_name='unidademaxflora',
            name='espaco',
        ),
        # Remove iptu_tcrs
        migrations.RemoveField(
            model_name='unidademaxflora',
            name='iptu_tcrs',
        ),
        # Adiciona iptu
        migrations.AddField(
            model_name='unidademaxflora',
            name='iptu',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        # Adiciona tcrs
        migrations.AddField(
            model_name='unidademaxflora',
            name='tcrs',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
