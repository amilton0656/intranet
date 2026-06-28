from django.db import models


class Empreendimento(models.Model):
    nome = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    id_empreendimento_ext = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'viab_empreendimentos'
        verbose_name = 'Empreendimento'
        verbose_name_plural = 'Empreendimentos'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def pode_excluir(self):
        return not self.estudos.exists()


class Tipo(models.Model):
    descricao = models.CharField(max_length=100)

    class Meta:
        db_table = 'viab_tipos'
        verbose_name = 'Tipo'
        verbose_name_plural = 'Tipos'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class Custo(models.Model):
    descricao = models.CharField(max_length=200)
    distrib = models.BooleanField(default=False)

    class Meta:
        db_table = 'viab_custos'
        verbose_name = 'Custo'
        verbose_name_plural = 'Custos'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class Curva(models.Model):
    descricao = models.CharField(max_length=200)

    class Meta:
        db_table = 'viab_curvas'
        verbose_name = 'Curva'
        verbose_name_plural = 'Curvas'
        ordering = ['descricao']

    def __str__(self):
        return self.descricao


class CurvaMes(models.Model):
    curva = models.ForeignKey(Curva, on_delete=models.CASCADE, related_name='meses')
    curva_mes = models.IntegerField()
    curva_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    class Meta:
        db_table = 'viab_curvas_meses'
        verbose_name = 'Mês da Curva'
        verbose_name_plural = 'Meses da Curva'
        ordering = ['curva_mes']
        unique_together = [['curva', 'curva_mes']]

    def __str__(self):
        return f'{self.curva} - Mês {self.curva_mes}: {self.curva_perc}%'


class Estudo(models.Model):
    TIPO_PRECO_REAL = 1
    TIPO_PRECO_PRIVATIVO = 2
    TIPO_PRECO_CHOICES = [
        (TIPO_PRECO_REAL, 'Área Real'),
        (TIPO_PRECO_PRIVATIVO, 'Área Privativa'),
    ]

    RECEITA_POR_CONFIG = 1
    RECEITA_POR_UNIDADE = 2
    RECEITA_CHOICES = [
        (RECEITA_POR_CONFIG, 'Por Configuração'),
        (RECEITA_POR_UNIDADE, 'Por Unidade'),
    ]

    CUSTO_M2_REAL = 1
    CUSTO_M2_PRIV_PERMU = 2
    CUSTO_M2_EQUIV = 3
    CUSTO_M2_CHOICES = [
        (CUSTO_M2_REAL, 'Área Real'),
        (CUSTO_M2_PRIV_PERMU, 'Área Privativa + Permutada'),
        (CUSTO_M2_EQUIV, 'Área Total Equivalente'),
    ]

    empreendimento = models.ForeignKey(
        Empreendimento, on_delete=models.PROTECT, related_name='estudos'
    )
    planilha = models.CharField(max_length=200)
    dt_base = models.CharField(max_length=6, help_text='Formato MMAAAA')

    # Preços / Receitas
    tipo_preco_venda = models.IntegerField(choices=TIPO_PRECO_CHOICES, default=TIPO_PRECO_REAL)
    area_real_total = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    area_priv_total = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    simulacao_preco01_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    simulacao_preco02_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    simulacao_preco03_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    simulacao_preco04_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    receita_tipo = models.IntegerField(choices=RECEITA_CHOICES, default=RECEITA_POR_CONFIG)
    investidor_partic = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    margem_negocial = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    # Construção
    inicio_construcao = models.IntegerField(default=0, help_text='Mês de início')
    tempo_construcao = models.IntegerField(default=0, help_text='Duração em meses')
    pre_lancamento = models.IntegerField(default=0, help_text='Meses antes do lançamento')
    lancamento = models.IntegerField(default=0, help_text='Mês de lançamento')
    custo_m2_valor = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    custo_m2_tipo = models.IntegerField(choices=CUSTO_M2_CHOICES, default=CUSTO_M2_REAL)
    area_equivalente_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    # Histórico de custo
    indice_reajuste = models.DecimalField(max_digits=10, decimal_places=4, default=1, help_text='Índice de reajuste')
    valor_cub = models.DecimalField(max_digits=14, decimal_places=4, default=0, help_text='Valor do CUB (R$)')

    # Custos percentuais
    perc_itbi = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    perc_despesas = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    perc_marketing = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    perc_corretagem = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    perc_impostos = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    perc_tx_adm = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    perc_assistencia = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    # Terreno
    terreno_area = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    terreno_valor = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cu_terreno_valor = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cu_terreno_desemb = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    cu_terreno_cor = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    terreneiro_invest = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    terreneiro_valor_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    # Permuta
    area_permutada = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    permu_fin_perc_receita = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    permu_fin_perc_comissao = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    permu_fin_perc_marketing = models.DecimalField(max_digits=8, decimal_places=4, default=0)

    # Financiamento
    tx_vp = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    tx_vp_ck = models.BooleanField(default=False)
    tx_securitizacao = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    tx_securitizacao_ck = models.BooleanField(default=False)
    tx_financ_cliente = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    tx_financ_cliente_ck = models.BooleanField(default=False)
    tx_financ_producao = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    tx_financ_producao_ck = models.BooleanField(default=False)
    tx_cap_giro = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    tx_cap_giro_ck = models.BooleanField(default=False)

    # Custos fixos (valores)
    projetos_valor = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    perc_projetos = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text='% sobre custo de construção')
    indice_construcao = models.DecimalField(max_digits=14, decimal_places=4, default=0, help_text='Índice de Construção / Solo Criado')
    terreno_valor_base_itbi = models.DecimalField(max_digits=14, decimal_places=4, default=0, help_text='Base para cálculo do ITBI')

    # Checkboxes de habilitação de custos
    projetos_ck = models.BooleanField(default=True)
    indice_ck = models.BooleanField(default=True)
    itbi_ck = models.BooleanField(default=True)
    despesas_ck = models.BooleanField(default=True)
    marketing_ck = models.BooleanField(default=True)
    corretagem_ck = models.BooleanField(default=True)
    impostos_ck = models.BooleanField(default=True)
    assistencia_ck = models.BooleanField(default=True)
    tx_adm_ck = models.BooleanField(default=True)
    terreno_desemb_ck = models.BooleanField(default=True)
    terreno_cor_ck = models.BooleanField(default=True)

    # Custo administrativo
    tx_adm_area_constr_ck = models.BooleanField(default=False)
    custo_adm_exclusao = models.BooleanField(default=False)

    # Capital Próprio
    capital_proprio = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    capital_proprio_ck = models.BooleanField(default=False)

    # Financiamento à Produção (parâmetros adicionais)
    financ_prod_perc_construido = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text='% construído para liberar')
    financ_prod_perc_vendido = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text='% vendido para liberar')
    financ_prod_perc_financiamento = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text='% do custo financiado')
    financ_prod_carencia = models.IntegerField(default=0, help_text='Carência em meses')
    financ_prod_qtde_parcelas = models.IntegerField(default=0, help_text='Qtde de parcelas')

    # Tipo da Receita
    receita_final = models.BooleanField(default=False, help_text='False=Inicial / True=Final')

    # Auditoria
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'viab_estudos'
        verbose_name = 'Estudo'
        verbose_name_plural = 'Estudos'
        ordering = ['empreendimento__nome', 'planilha']

    def __str__(self):
        return f'{self.empreendimento} - {self.planilha}'


class ConfigAgrupamento(models.Model):
    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name='agrupamentos')
    descricao = models.CharField(max_length=200)
    ordem = models.IntegerField(default=0)

    class Meta:
        db_table = 'viab_config_agrupamentos'
        verbose_name = 'Agrupamento'
        verbose_name_plural = 'Agrupamentos'
        ordering = ['ordem', 'descricao']

    def __str__(self):
        return self.descricao


class Config(models.Model):
    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name='configuracoes')
    tipo = models.ForeignKey(Tipo, on_delete=models.PROTECT, null=True, blank=True)
    agrupamento = models.ForeignKey(
        ConfigAgrupamento, on_delete=models.SET_NULL, null=True, blank=True
    )
    config_qtde_total = models.IntegerField(default=0)
    config_qtde_permu = models.IntegerField(default=0)
    config_qtde_imob = models.IntegerField(default=0)
    config_area_real = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    config_area_priv = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    config_valor_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    config_fechado = models.BooleanField(default=False, help_text='Preço fechado por unidade')
    config_ge = models.BooleanField(default=False, help_text='É garagem')

    class Meta:
        db_table = 'viab_config'
        verbose_name = 'Configuração'
        verbose_name_plural = 'Configurações'

    def clean(self):
        from django.core.exceptions import ValidationError
        if (self.config_qtde_permu + self.config_qtde_imob) > self.config_qtde_total:
            raise ValidationError(
                'Soma de permutadas e imobilizadas não pode exceder o total.'
            )

    def __str__(self):
        return f'{self.tipo} - {self.config_qtde_total} un.'


class Construcao(models.Model):
    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name='construcoes')
    curva = models.ForeignKey(Curva, on_delete=models.PROTECT, null=True, blank=True)
    descricao = models.CharField(max_length=200, blank=True)
    constru_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text='% do custo')
    constru_inicio = models.IntegerField(default=0, help_text='Mês de início')
    custo_m2 = models.DecimalField(max_digits=14, decimal_places=4, default=0)

    class Meta:
        db_table = 'viab_constru'
        verbose_name = 'Construção'
        verbose_name_plural = 'Construções'
        ordering = ['constru_inicio']

    def __str__(self):
        return f'{self.descricao} ({self.constru_perc}%)'


class Distribuicao(models.Model):
    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name='distribuicoes')
    custo = models.ForeignKey(Custo, on_delete=models.PROTECT)
    custo_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    custo_qtde = models.IntegerField(default=1, help_text='Meses de distribuição')
    custo_inicio = models.IntegerField(default=0, help_text='Mês de início')

    class Meta:
        db_table = 'viab_distribuicao'
        verbose_name = 'Distribuição de Custo'
        verbose_name_plural = 'Distribuições de Custo'

    def __str__(self):
        return f'{self.custo} - {self.custo_perc}% em {self.custo_qtde} meses'


class ParamVendas(models.Model):
    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name='params_vendas')
    descricao = models.CharField(max_length=200, blank=True)
    referencia = models.CharField(max_length=100, blank=True)
    preco_venda = models.DecimalField(max_digits=14, decimal_places=4, default=0)
    preco_venda_ref = models.IntegerField(default=1)
    tipo_financiamento = models.IntegerField(default=1)

    # Ato
    ato_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    ato_qtde = models.IntegerField(default=1)

    # Parcelas
    parc_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    parc_qtde = models.IntegerField(default=0)
    parc_apos = models.IntegerField(default=0)

    # Reforços
    ref_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    ref_qtde = models.IntegerField(default=0)
    ref_interv = models.IntegerField(default=0)

    # Chaves
    cha_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    cha_apos = models.IntegerField(default=0)

    # Financiamento 1 (parcelas)
    fin_parc_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    fin_parc_qtde = models.IntegerField(default=0)
    fin_parc_apos = models.IntegerField(default=0)

    # Financiamento 2 (reforços)
    fin_ref_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    fin_ref_qtde = models.IntegerField(default=0)
    fin_ref_interv = models.IntegerField(default=0)

    class Meta:
        db_table = 'viab_paramvendas'
        verbose_name = 'Parâmetro de Venda'
        verbose_name_plural = 'Parâmetros de Venda'

    def total_perc(self):
        return (
            self.ato_perc + self.parc_perc + self.ref_perc + self.cha_perc
            + self.fin_parc_perc + self.fin_ref_perc
        )

    def __str__(self):
        return self.descricao or f'Param #{self.pk}'


class Velocidade(models.Model):
    estudo = models.ForeignKey(Estudo, on_delete=models.CASCADE, related_name='velocidades')
    agrupamento = models.ForeignKey(
        ConfigAgrupamento, on_delete=models.SET_NULL, null=True, blank=True
    )
    param_vendas = models.ForeignKey(
        ParamVendas, on_delete=models.PROTECT, null=True, blank=True
    )
    veloc_perc = models.DecimalField(max_digits=8, decimal_places=4, default=0, help_text='% do total')
    veloc_qtde = models.IntegerField(default=0, help_text='Qtde de meses')
    veloc_inicio = models.IntegerField(default=0, help_text='Mês de início')

    class Meta:
        db_table = 'viab_veloc'
        verbose_name = 'Velocidade de Venda'
        verbose_name_plural = 'Velocidades de Venda'
        ordering = ['veloc_inicio']

    def __str__(self):
        return f'{self.veloc_perc}% a partir do mês {self.veloc_inicio}'
