from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.indices.models import Indice, IndiceData

DATA_ROWS = [
    ("09/2025", "R$ 2.993,04", "0,50 %", "R$ 2.787,88", "0,41 %"),
    ("08/2025", "R$ 2.978,02", "0,42 %", "R$ 3.181,03", "0,34 %"),
    ("07/2025", "R$ 2.965,54", "1,06 %", "R$ 3.170,14", "1,00 %"),
    ("06/2025", "R$ 2.934,53", "0,38 %", "R$ 3.138,86", "0,31 %"),
    ("05/2025", "R$ 2.923,52", "0,25 %", "R$ 3.129,12", "0,21 %"),
    ("04/2025", "R$ 2.916,12", "0,28 %", "R$ 3.122,59", "0,29 %"),
    ("03/2025", "R$ 2.907,85", "0,23 %", "R$ 3.113,61", "0,23 %"),
    ("02/2025", "R$ 2.901,09", "0,46 %", "R$ 3.106,60", "0,42 %"),
    ("01/2025", "R$ 2.887,91", "0,67 %", "R$ 3.093,54", "0,55 %"),
    ("12/2024", "R$ 2.868,56", "0,17 %", "R$ 3.076,64", "0,05 %"),
    ("11/2024", "R$ 2.863,73", "0,62 %", "R$ 3.075,23", "0,45 %"),
    ("10/2024", "R$ 2.846,12", "0,16 %", "R$ 3.061,34", "0,07 %"),
]

# Map the already existing indices (primary keys 1..4).
INDEX_ID_MAP = {
    "res_value": 1,   # CUB Residencial - Valor
    "res_percent": 2, # CUB Residencial - Percentual
    "com_value": 3,   # CUB Comercial - Valor
    "com_percent": 4, # CUB Comercial - Percentual
}

VALUE_MAPPING = (
    ("res_value", 1),
    ("res_percent", 2),
    ("com_value", 3),
    ("com_percent", 4),
)

class Command(BaseCommand):
    help = "Populate indices_datas with the provided CUB values."

    def handle(self, *args, **options):
        indices = self._load_existing_indices()
        created, updated = self._load_rows(indices)
        self.stdout.write(self.style.SUCCESS(
            f"IndiceData rows -> created: {created}, updated: {updated}."
        ))

    def _load_existing_indices(self):
        indices = {}
        for key, pk in INDEX_ID_MAP.items():
            try:
                indices[key] = Indice.objects.get(pk=pk)
            except Indice.DoesNotExist as exc:
                raise CommandError(
                    f"Indice id={pk} (mapped as '{key}') was not found."
                ) from exc
        return indices

    def _load_rows(self, indices):
        created = 0
        updated = 0
        for row in DATA_ROWS:
            month_year = row[0]
            data_ref = datetime.strptime(month_year, "%m/%Y").date()
            for key, column_index in VALUE_MAPPING:
                raw_value = row[column_index]
                value = self._parse_decimal(raw_value)
                indice = indices[key]
                _, was_created = IndiceData.objects.update_or_create(
                    indice=indice,
                    data=data_ref,
                    defaults={"valor": value},
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
        return created, updated

    def _parse_decimal(self, raw_value):
        cleaned = (
            raw_value.replace("R$", "")
            .replace("%", "")
            .replace(" ", "")
            .replace(".", "")
            .replace(",", ".")
        )
        if not cleaned:
            raise ValueError(f"Could not parse decimal value from '{raw_value}'.")
        return Decimal(cleaned)
