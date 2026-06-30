"""
Motor de cálculo de viabilidade econômica.
Equivalente ao VIAB_Rotinas.pas do sistema Delphi original.
"""
from decimal import Decimal
from dataclasses import dataclass, field
from typing import List, Optional
import math


TAM_FLUXO = 240  # máximo de meses suportado


@dataclass
class CelulaFluxo:
    mey: int = 0        # mês inteiro (offset)
    mex: str = ''       # mês como string MM/AAAA
    valor: float = 0.0
    juros: float = 0.0
    vp: float = 0.0
    curva: float = 0.0
    area: float = 0.0
    custo_m2: float = 0.0


# Índices das linhas do fluxo financeiro
class Linha:
    MES_REF = 0
    RECEITAS = 1
    CONSTRUCAO = 2
    PROJETOS = 3
    TX_ADM = 4
    ASSIST_TECNICA = 5
    MARKETING = 6
    CORRETAGEM = 7
    IMPOSTOS = 8
    TERRENO_ITBI = 9
    TERRENO_DESEMB = 10
    TERRENO_CORRET = 11
    INDICES = 12
    DESPESAS = 13
    FIN_PROD_RECEITA = 21
    FIN_PROD_DESEMB = 22
    FIN_PROD_JUROS = 23
    CAP_GIRO_APORTE = 31
    CAP_GIRO_DESEMB = 32
    CAP_GIRO_JUROS = 33
    FLUXO_CAIXA = 40
    FLUXO_ACUM = 41
    FLUXO_VP = 42


def taxa_ano_to_mes(taxa_anual: float) -> float:
    """Converte taxa anual (%) para mensal (%)."""
    if taxa_anual <= 0:
        return 0.0
    return (math.pow(1 + taxa_anual / 100, 1 / 12) - 1) * 100


def parse_dt_base(dt_base: str):
    """Converte MMAAAA para (mes, ano)."""
    if not dt_base or len(dt_base) != 6:
        return 1, 2024
    try:
        mes = int(dt_base[:2])
        ano = int(dt_base[2:])
        return mes, ano
    except ValueError:
        return 1, 2024


def mes_para_str(mes_offset: int, mes_base: int, ano_base: int) -> str:
    """Converte offset de mês para string MM/AAAA."""
    total = (ano_base - 1) * 12 + mes_base + mes_offset
    ano = (total - 1) // 12 + 1
    mes = (total - 1) % 12 + 1
    return f'{mes:02d}/{ano:04d}'


class CalculadorViabilidade:
    """
    Processa um Estudo e produz o fluxo financeiro completo.
    """

    def __init__(self, estudo):
        self.estudo = estudo
        self.fluxo: List[List[CelulaFluxo]] = [
            [CelulaFluxo() for _ in range(TAM_FLUXO)]
            for _ in range(46)
        ]
        self.tamanho_ff = 0
        self.mes_base, self.ano_base = parse_dt_base(estudo.dt_base)

        # Totais calculados
        self.und_total = 0
        self.und_permu = 0
        self.und_imob = 0
        self.und_avenda = 0
        self.gar_total = 0

        self.area_real_total = float(estudo.area_real_total)
        self.area_priv_total = float(estudo.area_priv_total)
        self.area_real_final = 0.0
        self.area_priv_final = 0.0
        self.area_permutada = float(estudo.area_permutada)
        self.area_equivalente = 0.0

        self.rec_total = 0.0
        self.rec_permu = 0.0
        self.rec_imob = 0.0
        self.rec_liq = 0.0

        self.custo_construcao = 0.0
        self.custo_total = 0.0
        self.custo_m2_real = 0.0
        self.custo_m2_priv = 0.0
        self.custo_m2_equiv = 0.0

        self.preco_medio_m2 = 0.0
        self.preco_medio_unid = 0.0
        self.eficiencia = 0.0

        self.resultado_bruto = 0.0
        self.resultado_liq = 0.0
        self.margem_bruta = 0.0
        self.margem_liq = 0.0
        self.tir_mensal = 0.0
        self.vpl = 0.0
        self.cu_terreno_desemb = 0.0

        # Custos individuais (calculados em calc_custos, usados em resumo())
        self.cu_itbi = 0.0
        self.cu_despesas = 0.0
        self.cu_marketing = 0.0
        self.cu_corretagem = 0.0
        self.cu_impostos = 0.0
        self.cu_assistencia = 0.0
        self.cu_tx_adm = 0.0

    # ------------------------------------------------------------------
    # Cálculo de Configurações / Receitas
    # ------------------------------------------------------------------

    def calc_config(self):
        configs = list(self.estudo.configuracoes.select_related('tipo', 'agrupamento').all())

        self.und_total = self.und_permu = self.und_imob = self.und_avenda = 0
        self.gar_total = 0
        self.area_real_total = self.area_priv_total = 0.0
        self.rec_total = self.rec_permu = self.rec_imob = 0.0
        self.rec_por_agrupamento: dict[int, float] = {}  # agrupamento_id → receita líquida

        for c in configs:
            qtde = c.config_qtde_total
            qtde_permu = c.config_qtde_permu
            qtde_imob = c.config_qtde_imob
            area_r = float(c.config_area_real)
            area_p = float(c.config_area_priv)
            valor_m2 = float(c.config_valor_m2)

            if c.config_ge:
                self.gar_total += qtde
                continue

            self.und_total += qtde
            self.und_permu += qtde_permu
            self.und_imob += qtde_imob
            self.und_avenda += (qtde - qtde_permu - qtde_imob)
            self.area_real_total += qtde * area_r
            self.area_priv_total += qtde * area_p

            if c.config_fechado:
                valor_und = valor_m2  # preço fechado por unidade
            else:
                tipo_preco = self.estudo.tipo_preco_venda
                if tipo_preco == 1:
                    valor_und = area_r * valor_m2
                else:
                    valor_und = area_p * valor_m2

            rec_und = valor_und * qtde
            rec_und_liq = valor_und * (qtde - qtde_permu - qtde_imob)
            self.rec_total += rec_und
            self.rec_permu += valor_und * qtde_permu
            self.rec_imob += valor_und * qtde_imob

            if c.agrupamento_id:
                self.rec_por_agrupamento[c.agrupamento_id] = (
                    self.rec_por_agrupamento.get(c.agrupamento_id, 0.0) + rec_und_liq
                )

        self.rec_liq = self.rec_total - self.rec_permu - self.rec_imob
        self.area_real_final = self.area_real_total
        self.area_priv_final = self.area_priv_total

        perc_equiv = float(self.estudo.area_equivalente_perc)
        if perc_equiv > 0:
            self.area_equivalente = self.area_real_final * perc_equiv / 100

        if self.und_total > 0:
            self.preco_medio_unid = self.rec_total / self.und_total
        area_base_preco = (
            self.area_priv_final
            if self.estudo.tipo_preco_venda == 2 and self.area_priv_final > 0
            else self.area_real_final
        )
        if area_base_preco > 0:
            self.preco_medio_m2 = self.rec_total / area_base_preco
        if self.area_real_final > 0 and self.area_priv_final > 0:
            self.eficiencia = self.area_priv_final / self.area_real_final

    # ------------------------------------------------------------------
    # Cálculo de Construção
    # ------------------------------------------------------------------

    def _area_construcao(self):
        tipo = self.estudo.custo_m2_tipo
        if tipo == 1:
            return self.area_real_final
        elif tipo == 2:
            return self.area_priv_final + self.area_permutada
        else:
            return self.area_equivalente

    def calc_construcao(self):
        area = self._area_construcao()
        self.custo_construcao = 0.0

        for c in self.estudo.construcoes.select_related('curva').all():
            custo = area * float(c.constru_perc) * float(c.custo_m2) / 100
            self.custo_construcao += custo

        if self.area_real_final > 0:
            self.custo_m2_real = self.custo_construcao / self.area_real_final
        if self.area_priv_final > 0:
            self.custo_m2_priv = self.custo_construcao / self.area_priv_final
        if self.area_equivalente > 0:
            self.custo_m2_equiv = self.custo_construcao / self.area_equivalente

    # ------------------------------------------------------------------
    # Cálculo de Custos
    # ------------------------------------------------------------------

    def calc_custos(self):
        from collections import defaultdict
        e = self.estudo
        rec = self.rec_liq
        terreno = float(e.terreno_valor)
        cc = self.custo_construcao

        # Terreno (Desembolso Líquido) = Terreno Valor − Investimento Terreneiro
        self.cu_terreno_desemb = terreno - float(e.terreneiro_invest)

        base_itbi = float(e.terreno_valor_base_itbi) if float(e.terreno_valor_base_itbi) > 0 else terreno

        # Calcula e armazena cada custo individual (evita recalcular em resumo())
        self.cu_itbi       = float(e.perc_itbi)        * base_itbi / 100
        self.cu_despesas   = float(e.perc_despesas)    * rec       / 100
        self.cu_marketing  = float(e.perc_marketing)   * rec       / 100
        self.cu_corretagem = float(e.perc_corretagem)  * rec       / 100
        self.cu_impostos   = float(e.perc_impostos)    * rec       / 100
        self.cu_assistencia= float(e.perc_assistencia) * cc        / 100
        self.cu_tx_adm     = float(e.perc_tx_adm)      * cc        / 100

        # Mapa: nome do custo → (valor calculado, campo checkbox que habilita)
        itens = [
            ('Projetos / Aprovação',                float(e.projetos_valor),    e.projetos_ck),
            ('Terreno (Desembolso Líquido)',         self.cu_terreno_desemb,     e.terreno_desemb_ck),
            ('Terreno (Corretagem)',                 float(e.cu_terreno_cor),    e.terreno_cor_ck),
            ('Índice de Construção / Solo Criado',   float(e.indice_construcao), e.indice_ck),
            ('Terreno (ITBI)',                       self.cu_itbi,               e.itbi_ck),
            ('Despesas Diversas',                    self.cu_despesas,           e.despesas_ck),
            ('Marketing',                            self.cu_marketing,          e.marketing_ck),
            ('Corretagem sobre Unidades',            self.cu_corretagem,         e.corretagem_ck),
            ('Impostos Federais (Lucro Presumido)',  self.cu_impostos,           e.impostos_ck),
            ('Assistência Técnica',                  self.cu_assistencia,        e.assistencia_ck),
            ('Taxa de Administração',                self.cu_tx_adm,             e.tx_adm_ck),
        ]

        # Soma percentual de distribuição por custo
        distrib_perc = defaultdict(float)
        for d in e.distribuicoes.select_related('custo').all():
            distrib_perc[d.custo.descricao] += float(d.custo_perc)

        # CUSTO TOTAL = Construção + Σ(valor × perc_distribuição / 100)
        # Checkbox desativado → item excluído do total
        # Item ausente na Distribuição → entra com 100%
        self.custo_total = cc
        for desc, valor, ck in itens:
            if not ck:
                continue
            perc = distrib_perc.get(desc, 100.0)
            self.custo_total += valor * perc / 100

        self.resultado_bruto = self.rec_liq - self.custo_total
        self.resultado_liq   = self.resultado_bruto  # Lucro Líquido = Receita Líq. - Custo Total
        if self.rec_liq > 0:
            self.margem_bruta = self.resultado_bruto / self.rec_liq * 100
            self.margem_liq   = self.margem_bruta

    # ------------------------------------------------------------------
    # Montagem do Fluxo Financeiro
    # ------------------------------------------------------------------

    def _set_mes_ref(self):
        for mes in range(TAM_FLUXO):
            c = self.fluxo[Linha.MES_REF][mes]
            c.mey = mes
            c.mex = mes_para_str(mes, self.mes_base, self.ano_base)

    def _incluir_construcao(self):
        area = self._area_construcao()
        for constru in self.estudo.construcoes.select_related('curva').prefetch_related('curva__meses').all():
            valor_total = area * float(constru.constru_perc) * float(constru.custo_m2) / 100
            if constru.curva:
                for cm in constru.curva.meses.all():
                    mes = constru.constru_inicio + cm.curva_mes
                    if 0 <= mes < TAM_FLUXO:
                        self.fluxo[Linha.CONSTRUCAO][mes].valor += (
                            valor_total * float(cm.curva_perc) / 100
                        )
                        self.tamanho_ff = max(self.tamanho_ff, mes + 1)

    def _incluir_velocidade(self):
        for veloc in self.estudo.velocidades.select_related('agrupamento').all():
            if veloc.veloc_qtde <= 0:
                continue
            base = (
                self.rec_por_agrupamento.get(veloc.agrupamento_id, 0.0)
                if veloc.agrupamento_id
                else self.rec_liq
            )
            valor_agrup = base * float(veloc.veloc_perc) / 100
            valor_mes = valor_agrup / veloc.veloc_qtde
            for i in range(veloc.veloc_qtde):
                mes = veloc.veloc_inicio + i
                if 0 <= mes < TAM_FLUXO:
                    self.fluxo[Linha.RECEITAS][mes].valor += valor_mes
                    self.tamanho_ff = max(self.tamanho_ff, mes + 1)

    def _incluir_custos_percentuais(self):
        e = self.estudo
        inicio_obra = int(e.inicio_construcao)
        tempo_obra = int(e.tempo_construcao) or 1
        entrega = inicio_obra + tempo_obra

        def distribuir(linha: int, valor: float, inicio: int = 0, meses: int = 1):
            if valor <= 0 or meses <= 0:
                return
            v_mes = valor / meses
            for i in range(meses):
                mes = inicio + i
                if 0 <= mes < TAM_FLUXO:
                    self.fluxo[linha][mes].valor += v_mes
                    self.tamanho_ff = max(self.tamanho_ff, mes + 1)

        # Mapa: descrição do custo → (checkbox, Linha, valor_total, inicio_default, meses_default)
        CUSTO_MAP = {
            'Projetos / Aprovação':                 (e.projetos_ck,       Linha.PROJETOS,       float(e.projetos_valor),    0,           1),
            'Terreno (Desembolso Líquido)':          (e.terreno_desemb_ck, Linha.TERRENO_DESEMB, self.cu_terreno_desemb,     0,           1),
            'Terreno (Corretagem)':                  (e.terreno_cor_ck,    Linha.TERRENO_CORRET, float(e.cu_terreno_cor),    0,           1),
            'Terreno (ITBI)':                        (e.itbi_ck,           Linha.TERRENO_ITBI,   self.cu_itbi,               0,           1),
            'Índice de Construção / Solo Criado':    (e.indice_ck,         Linha.INDICES,        float(e.indice_construcao), 0,           1),
            'Despesas Diversas':                     (e.despesas_ck,       Linha.DESPESAS,       self.cu_despesas,           inicio_obra, tempo_obra),
            'Marketing':                             (e.marketing_ck,      Linha.MARKETING,      self.cu_marketing,          inicio_obra, tempo_obra),
            'Corretagem sobre Unidades':             (e.corretagem_ck,     Linha.CORRETAGEM,     self.cu_corretagem,         inicio_obra, tempo_obra),
            'Impostos Federais (Lucro Presumido)':   (e.impostos_ck,       Linha.IMPOSTOS,       self.cu_impostos,           inicio_obra, tempo_obra),
            'Taxa de Administração':                 (e.tx_adm_ck,         Linha.TX_ADM,         self.cu_tx_adm,             inicio_obra, tempo_obra),
            'Assistência Técnica':                   (e.assistencia_ck,    Linha.ASSIST_TECNICA, self.cu_assistencia,        entrega,     60),
        }

        # Agrupa distribuições manuais por descrição do custo
        distrib_por_custo: dict[str, list] = {}
        for dist in e.distribuicoes.select_related('custo').all():
            distrib_por_custo.setdefault(dist.custo.descricao, []).append(dist)

        for nome, (ck, linha, valor_total, inicio_def, meses_def) in CUSTO_MAP.items():
            if not ck or valor_total <= 0:
                continue
            distribs = distrib_por_custo.get(nome)
            if distribs:
                for d in distribs:
                    distribuir(linha, valor_total * float(d.custo_perc) / 100,
                               d.custo_inicio, d.custo_qtde)
            else:
                distribuir(linha, valor_total, inicio_def, meses_def)

    def _calcular_fluxo_caixa(self):
        for mes in range(self.tamanho_ff):
            entradas = self.fluxo[Linha.RECEITAS][mes].valor
            saidas = sum(
                self.fluxo[linha][mes].valor
                for linha in [
                    Linha.CONSTRUCAO, Linha.PROJETOS, Linha.TX_ADM,
                    Linha.ASSIST_TECNICA, Linha.MARKETING, Linha.CORRETAGEM,
                    Linha.IMPOSTOS, Linha.TERRENO_ITBI, Linha.TERRENO_DESEMB,
                    Linha.TERRENO_CORRET, Linha.INDICES, Linha.DESPESAS,
                ]
            )
            self.fluxo[Linha.FLUXO_CAIXA][mes].valor = entradas - saidas

        acum = 0.0
        for mes in range(self.tamanho_ff):
            acum += self.fluxo[Linha.FLUXO_CAIXA][mes].valor
            self.fluxo[Linha.FLUXO_ACUM][mes].valor = acum

        self.resultado_fluxo_acum = acum  # acumulado do fluxo (não sobrescreve resultado_liq)

    def _calcular_vpl(self):
        taxa_mensal = taxa_ano_to_mes(float(self.estudo.tx_vp)) / 100
        if taxa_mensal <= 0:
            self.vpl = sum(
                self.fluxo[Linha.FLUXO_CAIXA][m].valor
                for m in range(self.tamanho_ff)
            )
            return
        vpl = 0.0
        for mes in range(self.tamanho_ff):
            fc = self.fluxo[Linha.FLUXO_CAIXA][mes].valor
            vpl += fc / math.pow(1 + taxa_mensal, mes + 1)
        self.vpl = vpl

    # ------------------------------------------------------------------
    # Ponto de entrada
    # ------------------------------------------------------------------

    def calcular(self):
        self.calc_config()
        self.calc_construcao()
        self.calc_custos()
        self._set_mes_ref()
        self._incluir_construcao()
        self._incluir_velocidade()
        self._incluir_custos_percentuais()
        self._calcular_fluxo_caixa()
        self._calcular_vpl()
        return self

    # ------------------------------------------------------------------
    # Resumo serializado (para templates / JSON)
    # ------------------------------------------------------------------

    def resumo(self) -> dict:
        indice        = float(self.estudo.indice_reajuste or 1)
        cub           = float(self.estudo.valor_cub or 0)
        custo_m2_calc = round(indice * cub, 4)
        area_equiv    = round(self.area_equivalente, 2)
        e             = self.estudo
        rec           = self.rec_liq
        cc            = self.custo_construcao

        # Valores já calculados em calc_custos() — apenas arredonda para exibição
        cu_itbi        = round(self.cu_itbi,        2)
        cu_despesas    = round(self.cu_despesas,    2)
        cu_marketing   = round(self.cu_marketing,   2)
        cu_corretagem  = round(self.cu_corretagem,  2)
        cu_impostos    = round(self.cu_impostos,    2)
        cu_assistencia = round(self.cu_assistencia, 2)
        cu_tx_adm      = round(self.cu_tx_adm,      2)

        return {
            'und_total': self.und_total,
            'und_avenda': self.und_avenda,
            'und_permu': self.und_permu,
            'und_imob': self.und_imob,
            'gar_total': self.gar_total,
            'area_real_total': round(self.area_real_total, 2),
            'area_priv_total': round(self.area_priv_total, 2),
            'area_equivalente': area_equiv,
            'eficiencia': round(self.eficiencia * 100, 2),
            'rec_total': round(self.rec_total, 2),
            'rec_permu': round(self.rec_permu, 2),
            'rec_liq': round(self.rec_liq, 2),
            'custo_construcao': round(self.custo_construcao, 2),
            'cu_terreno_desemb': round(self.cu_terreno_desemb, 2),
            'custo_total': round(self.custo_total, 2),
            'custo_m2_real': round(self.custo_m2_real, 2),
            'custo_m2_priv': round(self.custo_m2_priv, 2),
            'custo_m2_equiv': round(self.custo_m2_equiv, 2),
            'custo_m2_calc': custo_m2_calc,
            'preco_medio_m2': round(self.preco_medio_m2, 4),
            'preco_medio_unid': round(self.preco_medio_unid, 4),
            'area_real_media_unid': round(self.area_real_total / self.und_avenda, 4) if self.und_avenda else 0,
            'area_priv_media_unid': round(self.area_priv_total / self.und_avenda, 4) if self.und_avenda else 0,
            'eficiencia_decimal': round(self.eficiencia, 4),
            'resultado_bruto': round(self.resultado_bruto, 2),
            'resultado_liq': round(self.resultado_liq, 2),
            'margem_bruta': round(self.margem_bruta, 2),
            'margem_liq': round(self.margem_liq, 2),
            'vpl': round(self.vpl, 2),
            # Valores calculados por custo (para "Outros Custos")
            'cu_itbi':        cu_itbi,
            'cu_despesas':    cu_despesas,
            'cu_marketing':   cu_marketing,
            'cu_corretagem':  cu_corretagem,
            'cu_impostos':    cu_impostos,
            'cu_assistencia': cu_assistencia,
            'cu_tx_adm':      cu_tx_adm,
        }

    def fluxo_mensal(self) -> list:
        rows = []
        for mes in range(self.tamanho_ff):
            ref = self.fluxo[Linha.MES_REF][mes]
            rows.append({
                'mes': mes,
                'referencia': ref.mex,
                'receitas': round(self.fluxo[Linha.RECEITAS][mes].valor, 2),
                'construcao': round(self.fluxo[Linha.CONSTRUCAO][mes].valor, 2),
                'marketing': round(self.fluxo[Linha.MARKETING][mes].valor, 2),
                'corretagem': round(self.fluxo[Linha.CORRETAGEM][mes].valor, 2),
                'impostos': round(self.fluxo[Linha.IMPOSTOS][mes].valor, 2),
                'tx_adm': round(self.fluxo[Linha.TX_ADM][mes].valor, 2),
                'assist_tecnica': round(self.fluxo[Linha.ASSIST_TECNICA][mes].valor, 2),
                'despesas': round(self.fluxo[Linha.DESPESAS][mes].valor, 2),
                'projetos': round(self.fluxo[Linha.PROJETOS][mes].valor, 2),
                'indice': round(self.fluxo[Linha.INDICES][mes].valor, 2),
                'terreno': round(
                    self.fluxo[Linha.TERRENO_ITBI][mes].valor
                    + self.fluxo[Linha.TERRENO_DESEMB][mes].valor
                    + self.fluxo[Linha.TERRENO_CORRET][mes].valor, 2
                ),
                'fluxo_caixa': round(self.fluxo[Linha.FLUXO_CAIXA][mes].valor, 2),
                'fluxo_acum': round(self.fluxo[Linha.FLUXO_ACUM][mes].valor, 2),
            })
        return rows
