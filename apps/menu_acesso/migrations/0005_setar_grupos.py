from django.db import migrations

FINANCEIRO = {
    'bliss_resumo', 'bliss_unidades_full',
    'cota365:dashboard', 'cota365:unidades', 'cota365:vendas',
    'cota365:fluxo', 'cota365:parcelas', 'cota365:comissoes_cadastro',
}

ADMIN = {
    'incorporadora:empresa_list', 'incorporadora:empreendimento_list',
    'pessoas:pessoa_list', 'propostas:proposta_list', 'contratos:minuta_list',
    'incorporadora:importar_redirect', 'cota365:cartorio',
    'maxflora:tabela', 'usuario_list',
}


def setar_grupos(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    for url_name in FINANCEIRO:
        MenuItem.objects.filter(app='intranet', navbar='principal', url_name=url_name).update(grupo='financeiro')
    for url_name in ADMIN:
        MenuItem.objects.filter(app='intranet', navbar='principal', url_name=url_name).update(grupo='admin')


def reverter(apps, schema_editor):
    MenuItem = apps.get_model('menu_acesso', 'MenuItem')
    MenuItem.objects.filter(app='intranet', navbar='principal').update(grupo='')


class Migration(migrations.Migration):
    dependencies = [
        ('menu_acesso', '0004_menuitem_grupo'),
    ]
    operations = [
        migrations.RunPython(setar_grupos, reverter),
    ]
