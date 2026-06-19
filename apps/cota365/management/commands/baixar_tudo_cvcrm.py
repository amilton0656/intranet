"""
Baixa todos os CSVs do CV CRM em uma única sessão do Chrome.

O login é feito uma única vez no primeiro comando. Os demais
reconectam ao mesmo Chrome via CDP (porta 9222) sem nova autenticação.

Ordem de execução:
  1. baixar_tabela_cvcrm    → tabela.csv
  2. baixar_vendas_cvcrm    → vendas.csv
  3. baixar_fluxo_cvcrm     → fluxo.csv
  4. baixar_comissoes_cvcrm → comissoes.csv

Uso:
    python manage.py baixar_tudo_cvcrm
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


COMANDOS = [
    ('baixar_tabela_cvcrm',    'tabela.csv'),
    ('baixar_vendas_cvcrm',    'vendas.csv'),
    ('baixar_fluxo_cvcrm',     'fluxo.csv'),
    ('baixar_comissoes_cvcrm', 'comissoes.csv'),
]


class Command(BaseCommand):
    help = 'Baixa todos os CSVs do CV CRM em uma única sessão (login único).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apenas', type=str, default=None,
            help='Executa só um comando específico (ex: --apenas vendas)',
        )

    def handle(self, *args, **options):
        filtro = options.get('apenas')
        comandos = [
            (cmd, arq) for cmd, arq in COMANDOS
            if not filtro or filtro in cmd
        ]

        if not comandos:
            self.stdout.write(self.style.ERROR(f'Nenhum comando encontrado para --apenas={filtro}'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Iniciando download de {len(comandos)} relatório(s)...\n'
        ))

        erros = []
        for i, (cmd, arquivo) in enumerate(comandos, 1):
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'[{i}/{len(comandos)}] {cmd} → {arquivo}'
            ))
            try:
                call_command(cmd, stdout=self.stdout, stderr=self.stderr)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {arquivo} concluído\n'))
            except Exception as e:
                msg = str(e)
                self.stdout.write(self.style.ERROR(f'  ✗ {arquivo} FALHOU: {msg}\n'))
                erros.append((arquivo, msg))

        self.stdout.write('─' * 50)
        if erros:
            self.stdout.write(self.style.ERROR(f'{len(erros)} falha(s):'))
            for arq, err in erros:
                self.stdout.write(f'  {arq}: {err}')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Todos os {len(comandos)} arquivos baixados com sucesso!'
            ))
