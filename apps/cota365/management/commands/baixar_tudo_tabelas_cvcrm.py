"""
Baixa todos os PDFs de tabela de preços (Bliss + Cota 365) em uma única
sessão do Chrome — mesmo padrão do baixar_tudo_cvcrm, mas para os PDFs do
mapa de Disponibilidade em vez dos CSVs de relatório.

O login é feito uma única vez no primeiro comando. Os demais reconectam ao
mesmo Chrome via CDP (porta 9222) sem nova autenticação.

Ordem de execução:
  1. Bliss Living
  2. Cota 365 - Tabela Curta
  3. Cota 365 - Tabela Longa - 2D
  4. Cota 365 - Tabela Longa - Studios e Lojas

Uso:
    python manage.py baixar_tudo_tabelas_cvcrm
    python manage.py baixar_tudo_tabelas_cvcrm --apenas "Tabela Curta"
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


TABELAS = [
    ('Bliss Living', {}),
    ('Cota 365 - Tabela Curta', {
        'empreendimento_id': 3,
        # Nome real na página inclui prefixo "R00 -" e sufixo de mês/ano que
        # muda todo mês (ex: "R00 - Tabela Curta (Todas Tipologias) - Agosto
        # 2026"). Usar só o trecho estável, sem mês/ano, pra não quebrar
        # quando a CV CRM gerar a tabela do mês seguinte.
        'nome_tabela': 'Tabela Curta',
        'output': r'G:\Meu Drive\_intranet\tabelas\COTA 365 - Tabela Curta.pdf',
    }),
    ('Cota 365 - Tabela Longa - 2D', {
        'empreendimento_id': 3,
        'nome_tabela': 'Tabela Longa (2 Dorm)',
        'output': r'G:\Meu Drive\_intranet\tabelas\COTA 365 - Tabela Longa - 2D.pdf',
    }),
    ('Cota 365 - Tabela Longa - Studios e Lojas', {
        'empreendimento_id': 3,
        'nome_tabela': 'Tabela Longa (Studio e Lojas)',
        'output': r'G:\Meu Drive\_intranet\tabelas\COTA 365 - Tabela Longa - Studios e Lojas.pdf',
    }),
]


class Command(BaseCommand):
    help = 'Baixa todos os PDFs de tabela de preços (Bliss + Cota 365) em uma única sessão (login único).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apenas', type=str, default=None,
            help='Executa só uma tabela específica, por trecho do nome (ex: --apenas "Tabela Curta")',
        )

    def handle(self, *args, **options):
        filtro = options.get('apenas')
        tabelas = [
            (nome, kwargs) for nome, kwargs in TABELAS
            if not filtro or filtro.lower() in nome.lower()
        ]

        if not tabelas:
            self.stdout.write(self.style.ERROR(f'Nenhuma tabela encontrada para --apenas="{filtro}"'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Iniciando download de {len(tabelas)} tabela(s) de preço...\n'
        ))

        erros = []
        for i, (nome, kwargs) in enumerate(tabelas, 1):
            self.stdout.write(self.style.MIGRATE_HEADING(f'[{i}/{len(tabelas)}] {nome}'))
            try:
                call_command('baixar_tabela_disponibilidade_cvcrm', stdout=self.stdout, stderr=self.stderr, **kwargs)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {nome} concluído\n'))
            except Exception as e:
                msg = str(e)
                self.stdout.write(self.style.ERROR(f'  ✗ {nome} FALHOU: {msg}\n'))
                erros.append((nome, msg))

        self.stdout.write('─' * 50)
        if erros:
            self.stdout.write(self.style.ERROR(f'{len(erros)} falha(s):'))
            for nome, err in erros:
                self.stdout.write(f'  {nome}: {err}')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Todas as {len(tabelas)} tabelas baixadas com sucesso!'
            ))
