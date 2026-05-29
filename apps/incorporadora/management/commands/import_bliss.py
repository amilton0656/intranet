"""
Importa unidades do app Bliss para o app Incorporadora.

Uso:
    python manage.py import_bliss
    python manage.py import_bliss --limpar      # apaga unidades existentes antes de importar
    python manage.py import_bliss --dry-run     # simula sem salvar

O Empreendimento BLISS LIVING deve já existir no incorporadora (pk=2 por padrão).
Use --empreendimento=<pk> para especificar outro.
"""

import re
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.bliss.models import Bliss
from apps.incorporadora.models import Empreendimento, Bloco, Unidade


STATUS_MAP = {
    'disponível': 'disponivel',
    'disponivel': 'disponivel',
    'reservada':  'reservado',
    'reservado':  'reservado',
    'vendida':    'vendido',
    'vendido':    'vendido',
    'permuta':    'permuta',
    'bloqueada':  'bloqueado',
    'bloqueado':  'bloqueado',
    'qa':         'qa',
}

PERC_PERMUTA_LOJA = Decimal('0.12826')


def _parse_garagens(raw):
    """Extrai números de garagem do campo garagem do Bliss.

    Exemplos:
      'G10 Esp Coberta'        → ['G10']
      'G52/G52A Dupla Desc'    → ['G52', 'G52A']
      'G13/G21 Cob/Esp Cob'   → ['G13', 'G21']
      'G1 até G8'              → ['G1','G2','G3','G4','G5','G6','G7','G8']
    """
    if not raw or raw.strip() in ('', '- -', ' - - ', '-'):
        return []
    raw = raw.strip()
    # Range: G1 até G8
    m = re.match(r'G(\d+)\s+at[eé]\s+G(\d+)', raw, re.IGNORECASE)
    if m:
        return [f'G{i}' for i in range(int(m.group(1)), int(m.group(2)) + 1)]
    return re.findall(r'G\d+[A-Za-z]?', raw)


def _garagem_descricao(raw):
    """Extrai a descrição textual do campo garagem (ex: 'Esp Coberta')."""
    if not raw:
        return ''
    desc = re.sub(r'G\d+[A-Za-z]?', '', raw)
    desc = re.sub(r'\s*/\s*', ' ', desc)
    desc = re.sub(r'\bató?\b', '', desc, flags=re.IGNORECASE)
    return desc.strip(' /-').strip()


def _parse_hb(raw):
    """Extrai número do hobby box (ex: 'HB12' → 'HB12')."""
    if not raw or raw.strip() in ('', '- -', ' - - ', '-'):
        return None
    m = re.search(r'HB\d+', raw.strip())
    return m.group(0) if m else None


class Command(BaseCommand):
    help = 'Importa unidades do app Bliss para o Incorporadora'

    def add_arguments(self, parser):
        parser.add_argument(
            '--empreendimento', type=int, default=2,
            help='PK do Empreendimento no incorporadora (padrão: 2)',
        )
        parser.add_argument(
            '--limpar', action='store_true',
            help='Apaga todas as unidades do empreendimento antes de importar',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Simula a importação sem salvar nada',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        emp_pk   = options['empreendimento']
        limpar   = options['limpar']
        dry_run  = options['dry_run']

        try:
            empreendimento = Empreendimento.objects.get(pk=emp_pk)
        except Empreendimento.DoesNotExist:
            raise CommandError(f'Empreendimento pk={emp_pk} não encontrado.')

        self.stdout.write(f'Empreendimento: {empreendimento}')

        if limpar and not dry_run:
            qtde = Unidade.objects.filter(bloco__empreendimento=empreendimento).count()
            Unidade.objects.filter(bloco__empreendimento=empreendimento).delete()
            Bloco.objects.filter(empreendimento=empreendimento).delete()
            self.stdout.write(self.style.WARNING(f'  {qtde} unidades e blocos removidos.'))

        registros = list(Bliss.objects.all().order_by('bloco', 'unidade'))
        self.stdout.write(f'Registros Bliss: {len(registros)}')

        blocos_cache = {}
        criados = atualizados = garagens_c = hbs_c = erros = 0
        ordem_por_bloco = {}

        for reg in registros:
            bloco_nome = reg.bloco.strip()

            # ── Bloco ────────────────────────────────────────────────────────
            if bloco_nome not in blocos_cache:
                if not dry_run:
                    bloco, _ = Bloco.objects.get_or_create(
                        empreendimento=empreendimento,
                        nome=bloco_nome,
                    )
                    blocos_cache[bloco_nome] = bloco
                else:
                    blocos_cache[bloco_nome] = f'(bloco {bloco_nome})'

            bloco = blocos_cache[bloco_nome]

            # ── Unidade principal ─────────────────────────────────────────────
            num = reg.unidade.strip()
            if not num:
                erros += 1
                continue

            status      = STATUS_MAP.get((reg.situacao or '').strip().lower(), 'disponivel')
            is_loja     = num.lower() == 'loja'
            tipo        = 'loja' if is_loja else 'apartamento'
            perc_perm   = PERC_PERMUTA_LOJA if is_loja else Decimal('0')
            ordem       = ordem_por_bloco.get(bloco_nome, 0)
            ordem_por_bloco[bloco_nome] = ordem + 1

            if not dry_run:
                principal, criado = Unidade.objects.update_or_create(
                    bloco=bloco,
                    numero=num,
                    defaults={
                        'tipo':           tipo,
                        'tipologia':      (reg.tipologia or '').strip(),
                        'area_privativa': reg.area_privativa or Decimal('0'),
                        'valor_tabela':   reg.valor_tabela or Decimal('0'),
                        'perc_permuta':   perc_perm,
                        'status':         status,
                        'ordem':          ordem,
                    },
                )
                if criado:
                    criados += 1
                else:
                    atualizados += 1
            else:
                principal = None
                criados += 1

            # ── Garagens ──────────────────────────────────────────────────────
            nums_gar = _parse_garagens(reg.garagem or '')
            desc_gar = _garagem_descricao(reg.garagem or '')

            for g_num in nums_gar:
                if not dry_run:
                    Unidade.objects.update_or_create(
                        bloco=bloco,
                        numero=g_num,
                        defaults={
                            'tipo':              'garagem',
                            'unidade_principal': principal,
                            'descricao1':        desc_gar,
                            'status':            status,
                            'ordem':             ordem,
                        },
                    )
                garagens_c += 1

            # ── Hobby Boxes ───────────────────────────────────────────────────
            hb_num = _parse_hb(reg.deposito or '')
            if hb_num:
                if not dry_run:
                    Unidade.objects.update_or_create(
                        bloco=bloco,
                        numero=hb_num,
                        defaults={
                            'tipo':              'hobby_box',
                            'unidade_principal': principal,
                            'status':            status,
                            'ordem':             ordem,
                        },
                    )
                hbs_c += 1

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN — nada foi salvo.'))
            transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'\nResultado: {criados} unidades criadas, {atualizados} atualizadas, '
            f'{garagens_c} garagens, {hbs_c} hobby boxes, {erros} erros.'
        ))
