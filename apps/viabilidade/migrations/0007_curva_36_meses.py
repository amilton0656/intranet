from django.db import migrations

MESES = [
    (0,  '1.0100'),
    (1,  '1.1500'),
    (2,  '1.1700'),
    (3,  '1.2200'),
    (4,  '1.2800'),
    (5,  '1.3800'),
    (6,  '1.4500'),
    (7,  '1.4900'),
    (8,  '1.5600'),
    (9,  '1.6100'),
    (10, '1.6700'),
    (11, '1.7400'),
    (12, '1.8600'),
    (13, '1.9700'),
    (14, '2.0100'),
    (15, '2.0400'),
    (16, '2.2000'),
    (17, '2.5000'),
    (18, '2.6000'),
    (19, '2.9000'),
    (20, '3.0000'),
    (21, '3.1000'),
    (22, '3.3500'),
    (23, '3.8100'),
    (24, '4.1700'),
    (25, '4.3700'),
    (26, '4.7100'),
    (27, '5.0000'),
    (28, '4.8500'),
    (29, '4.3000'),
    (30, '4.0000'),
    (31, '3.8000'),
    (32, '3.6300'),
    (33, '3.5000'),
    (34, '3.3700'),
    (35, '2.9300'),
    (36, '2.3000'),
    (37, '1.0000'),
]


def aplicar(apps, schema_editor):
    Curva    = apps.get_model('viabilidade', 'Curva')
    CurvaMes = apps.get_model('viabilidade', 'CurvaMes')
    curva, _ = Curva.objects.get_or_create(descricao='36 MESES')
    CurvaMes.objects.filter(curva=curva).delete()
    CurvaMes.objects.bulk_create([
        CurvaMes(curva=curva, curva_mes=mes, curva_perc=perc)
        for mes, perc in MESES
    ])


def reverter(apps, schema_editor):
    Curva = apps.get_model('viabilidade', 'Curva')
    Curva.objects.filter(descricao='36 MESES').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('viabilidade', '0006_paramvendas_preco_ref_tipo_fin'),
    ]
    operations = [
        migrations.RunPython(aplicar, reverter),
    ]
