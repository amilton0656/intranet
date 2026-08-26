"""
Importa o CSV de faturamento (relatório de baixas de recebimento do Sienge).

Uso:
    python manage.py importar_faturamento
    python manage.py importar_faturamento --arquivo=/caminho/para/faturamento.csv
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.faturamento.importer import parse_csv, salvar_importacao


class Command(BaseCommand):
    help = 'Importa o CSV de faturamento (baixas de recebimento do Sienge).'

    def add_arguments(self, parser):
        parser.add_argument('--arquivo', type=str, default=None,
                             help='Caminho do CSV (padrão: faturamento.csv na raiz do projeto)')

    def handle(self, *args, **options):
        arquivo = options['arquivo'] or str(Path(settings.BASE_DIR) / 'faturamento.csv')
        if not Path(arquivo).exists():
            raise CommandError(f'Arquivo não encontrado: {arquivo}')

        self.stdout.write(f'Lendo {Path(arquivo).name}...')
        with open(arquivo, 'rb') as f:
            linhas = parse_csv(f)

        if not linhas:
            raise CommandError('Nenhuma linha válida encontrada no arquivo.')

        imp = salvar_importacao(Path(arquivo).name, linhas)

        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {len(linhas)} recebimentos salvos '
            f'(importação #{imp.pk} em {imp.importado_em:%d/%m/%Y %H:%M}).'
        ))
