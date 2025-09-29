from datetime import date
from decimal import Decimal, InvalidOperation
import calendar

from django.db import connection
from django.shortcuts import render

from datetime import date
import locale


class Uteis:
    def fetch_indices_data(self, id_indice, indice_data):
        """Fetch raw rows from indices_datas matching the given indice and date."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM indices_datas
                WHERE id_indice = %s AND data = %s
                """,
                [id_indice, indice_data],
            )
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    def fetch_indices_last_12_months(self, indices=(1, 2, 3, 4)):
        """Return the latest 12 months of data for the requested indices grouped by month."""
        today = date.today()
        latest_month = date(today.year, today.month, 1)

        start_year = latest_month.year
        start_month = latest_month.month - 11
        while start_month <= 0:
            start_month += 12
            start_year -= 1
        first_month = date(start_year, start_month, 1)

        placeholders = ', '.join(['%s'] * len(indices))
        query = f"""
            SELECT id_indice, data, valor
            FROM indices_datas
            WHERE id_indice IN ({placeholders})
              AND data BETWEEN %s AND %s
            ORDER BY data ASC, id_indice ASC
        """
        params = list(indices) + [first_month, latest_month]

        with connection.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

        grouped_by_month = {}
        for id_indice, data_ref, valor in rows:
            grouped_by_month.setdefault(data_ref, {})[id_indice] = valor

        history = []
        for data_ref in sorted(grouped_by_month.keys(), reverse=True):
            values = grouped_by_month[data_ref]
            history.append(
                {
                    "mes": data_ref.strftime("%m/%Y"),
                    "res_valor": self.format_currency_brl(values.get(1)),
                    "res_percentual": self.format_percentage(values.get(2)),
                    "com_valor": self.format_currency_brl(values.get(3)),
                    "com_percentual": self.format_percentage(values.get(4)),
                }
            )

        return history

    def format_currency_brl(self, value) -> str:
        try:
            amount = Decimal(value)
        except (InvalidOperation, TypeError):
            return "R$ 0,00"
        quantized = amount.quantize(Decimal("0.01"))
        formatted = f"{quantized:,.2f}"
        return f"R$ {formatted}".replace(",", "X").replace(".", ",").replace("X", ".")

    def format_percentage(self, value) -> str:
        try:
            amount = Decimal(value)
        except (InvalidOperation, TypeError):
            return "0,00 %"
        quantized = amount.quantize(Decimal("0.01"))
        formatted = f"{quantized:,.2f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} %"

    def format_number_ptbr(self, value, decimal_places=2) -> str:
        try:
            amount = Decimal(value)
        except (InvalidOperation, TypeError):
            return ("0," + "0" * decimal_places) if decimal_places else "0"

        if decimal_places == 0:
            quantized = amount.quantize(Decimal("1"))
            formatted = f"{quantized:,}"
        else:
            quantize_str = "0." + "0" * (decimal_places - 1) + "1"
            quantized = amount.quantize(Decimal(quantize_str))
            formatted = f"{quantized:,.{decimal_places}f}"

        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted

    def cubs_hoje(self):
        hoje = date.today()
        data = date(hoje.year, hoje.month, 1)

        indices1 = self.fetch_indices_data(1, data)
        indices2 = self.fetch_indices_data(2, data)
        indices3 = self.fetch_indices_data(1, data)
        indices4 = self.fetch_indices_data(2, data)

        return {
            "cubres": f"Residencial: {self.format_currency_brl(indices1[0]['valor'])} - {self.format_percentage(indices2[0]['valor'])}",
            "cubcom": f"Comercial: {self.format_currency_brl(indices3[0]['valor'])} - {self.format_percentage(indices4[0]['valor'])}",
            "mes": self.mes_atual_extenso(),
        }

    def mes_atual_extenso(self) -> str:
        hoje = date.today()
        try:
            original_locale = locale.setlocale(locale.LC_TIME)
        except locale.Error:
            original_locale = None

        for loc in ("pt_BR.UTF-8", "pt_BR.utf8", "pt_BR", "pt_BR.ISO8859-1"):
            try:
                locale.setlocale(locale.LC_TIME, loc)
                month_name = hoje.strftime("%B").capitalize()
                if original_locale:
                    locale.setlocale(locale.LC_TIME, original_locale)
                else:
                    try:
                        locale.setlocale(locale.LC_TIME, 'C')
                    except locale.Error:
                        pass
                return f"{month_name}/{hoje.year}"
            except locale.Error:
                continue

        if original_locale:
            try:
                locale.setlocale(locale.LC_TIME, original_locale)
            except locale.Error:
                pass
        else:
            try:
                locale.setlocale(locale.LC_TIME, 'C')
            except locale.Error:
                pass

        meses_pt = [
            "Janeiro", "Fevereiro", "Mar\u00e7o", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ]
        return f"{meses_pt[hoje.month - 1]}/{hoje.year}"
