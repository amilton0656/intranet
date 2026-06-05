from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.bliss.models import Bliss
from apps.incorporadora.models import Empreendimento, Unidade

SEP = '-' * 55


class Command(BaseCommand):
    help = 'Compara area_privativa das unidades BLISS LIVING entre app bliss e app incorporadora'

    def handle(self, *args, **options):
        try:
            emp = Empreendimento.objects.get(nome__icontains='bliss')
        except Empreendimento.DoesNotExist:
            self.stderr.write('Empreendimento BLISS LIVING nao encontrado.')
            return

        bliss_map = {
            b.unidade: b.area_privativa
            for b in Bliss.objects.all()
        }

        inc_map = {
            u.numero: u.area_privativa
            for u in Unidade.objects.filter(
                bloco__empreendimento=emp,
                tipo__in=['apartamento', 'sala', 'loja'],
                unidade_principal__isnull=True,
            )
        }

        todos = sorted(set(bliss_map) | set(inc_map))

        ZERO = Decimal('0')

        so_bliss    = [n for n in todos if n not in inc_map]
        so_inc      = [n for n in todos if n not in bliss_map]
        divergentes = [
            n for n in todos
            if n in bliss_map and n in inc_map and bliss_map[n] != inc_map[n]
        ]
        iguais = len(todos) - len(so_bliss) - len(so_inc) - len(divergentes)

        self.stdout.write(
            f'\nEmpreendimento: {emp}\n'
            f'Unidades no bliss:         {len(bliss_map):>4}\n'
            f'Unidades no incorporadora: {len(inc_map):>4}\n'
        )

        # -- So no bliss --
        if so_bliss:
            self.stdout.write(f'\n{SEP}\nSO NO BLISS ({len(so_bliss)} unidade(s))\n{SEP}')
            for n in so_bliss:
                self.stdout.write(f'  {n:<15}  bliss={bliss_map[n]:.2f}')

        # -- So no incorporadora --
        if so_inc:
            self.stdout.write(f'\n{SEP}\nSO NO INCORPORADORA ({len(so_inc)} unidade(s))\n{SEP}')
            for n in so_inc:
                self.stdout.write(f'  {n:<15}  inc={inc_map[n]:.2f}')

        # -- Areas divergentes --
        if divergentes:
            self.stdout.write(f'\n{SEP}\nAREAS DIVERGENTES ({len(divergentes)} unidade(s))\n{SEP}')
            self.stdout.write(f'  {"Unidade":<15} {"Bliss":>10} {"Incorporadora":>15} {"Diferenca":>12}')
            for n in divergentes:
                b    = bliss_map[n]
                i    = inc_map[n]
                diff = i - b
                self.stdout.write(f'  {n:<15} {b:>10.2f} {i:>15.2f} {diff:>+12.2f}')
        else:
            self.stdout.write('\nNenhuma area divergente encontrada.')

        # -- Totais --
        total_bliss   = sum(bliss_map.values(), ZERO)
        total_inc_all = sum(inc_map.values(), ZERO)

        self.stdout.write(
            f'\n{SEP}\nTOTAIS\n{SEP}\n'
            f'  Bliss:         {total_bliss:>10.2f} m2\n'
            f'  Incorporadora: {total_inc_all:>10.2f} m2  '
            f'(diff={total_inc_all - total_bliss:+.2f} m2)\n'
            f'\n'
            f'  Iguais: {iguais}  |  Divergentes: {len(divergentes)}  |  '
            f'So bliss: {len(so_bliss)}  |  So incorporadora: {len(so_inc)}\n'
        )
