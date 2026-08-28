"""
Importa o CSV de contas a receber (relatório de parcelas pendentes do Sienge).

Uso:
    python manage.py importar_areceber
    python manage.py importar_areceber --arquivo=/caminho/para/fat_areceber.csv
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.faturamento.importer import (
    parse_areceber_csv, recalcular_contratos, salvar_importacao_areceber,
)


class Command(BaseCommand):
    help = 'Importa o CSV de contas a receber (parcelas pendentes do Sienge).'

    def add_arguments(self, parser):
        parser.add_argument('--arquivo', type=str, default=None,
                             help='Caminho do CSV (padrão: fat_areceber.csv na raiz do projeto)')

    def handle(self, *args, **options):
        arquivo = options['arquivo'] or str(Path(settings.BASE_DIR) / 'fat_areceber.csv')
        if not Path(arquivo).exists():
            raise CommandError(f'Arquivo não encontrado: {arquivo}')

        self.stdout.write(f'Lendo {Path(arquivo).name}...')
        with open(arquivo, 'rb') as f:
            linhas = parse_areceber_csv(f)

        if not linhas:
            raise CommandError('Nenhuma linha válida encontrada no arquivo.')

        imp = salvar_importacao_areceber(Path(arquivo).name, linhas)
        recalcular_contratos()

        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {len(linhas)} parcelas pendentes salvas '
            f'(importação #{imp.pk} em {imp.importado_em:%d/%m/%Y %H:%M}).'
        ))
