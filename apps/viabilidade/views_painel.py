"""
Views do painel principal — interface única com 5 abas, grids HTMX e cálculo em tempo real.
"""
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import (
    Estudo, Empreendimento, Config, ConfigAgrupamento,
    Velocidade, Construcao, Distribuicao, ParamVendas,
    Curva, CurvaMes, Tipo, Custo,
)
from .calculos import CalculadorViabilidade


def parse_decimal(raw):
    """Converte string numérica (formato BR ou US) para Decimal."""
    if not raw:
        return Decimal('0')
    val = raw.replace('.', '').replace(',', '.') if ',' in raw else raw.replace(',', '')
    try:
        return Decimal(val)
    except Exception:
        return Decimal('0')


def _render_htmx(request, template_name, **ctx):
    """Helper para renderizar partial HTMX e retornar HttpResponse."""
    return HttpResponse(render_to_string(template_name, ctx, request=request))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resumo_calcular(estudo):
    try:
        return CalculadorViabilidade(estudo).calcular().resumo()
    except Exception:
        return {}


_MESES_PT = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ']


def _offset_para_str(mes_base, ano_base, offset):
    total = (ano_base - 1) * 12 + mes_base + offset
    ano = (total - 1) // 12 + 1
    mes = (total - 1) % 12 + 1
    return f'{_MESES_PT[mes-1]}/{ano}'


def _periodos(estudo):
    from .calculos import parse_dt_base
    mb, ab = parse_dt_base(estudo.dt_base)
    pre  = int(estudo.pre_lancamento or 0)
    lanc = int(estudo.lancamento or 0)
    ini  = int(estudo.inicio_construcao or 0)
    dur  = int(estudo.tempo_construcao or 0)
    return [
        ('Data Base',           estudo.dt_base,         _offset_para_str(mb, ab, 0),   0),
        ('Pré-Lançamento',      pre,                    _offset_para_str(mb, ab, pre),  pre),
        ('Lançamento',          lanc,                   _offset_para_str(mb, ab, lanc), lanc),
        ('Início Construção',   ini,                    _offset_para_str(mb, ab, ini),  ini),
        ('Tempo de Construção', dur,                    _offset_para_str(mb, ab, ini + dur - 1 if dur > 0 else ini), ini + dur - 1 if dur > 0 else ini),
    ]


def _taxa_am(taxa_aa: float) -> str:
    """Converte taxa anual (%) para mensal (%) formatada."""
    from .calculos import taxa_ano_to_mes
    if not taxa_aa:
        return '0,0000'
    am = taxa_ano_to_mes(taxa_aa)
    return f'{am:.4f}'.replace('.', ',')


def _taxas_financeiras(estudo):
    """Retorna lista de taxas com conversão anual → mensal para o template."""
    def tx(label, campo_aa, campo_ck, am_only=False, campo_am=None):
        val_aa = float(getattr(estudo, campo_aa, 0) or 0)
        am_str = _taxa_am(val_aa) if not am_only else None
        return {
            'label': label,
            'campo_aa': campo_aa,
            'val_aa': getattr(estudo, campo_aa, 0),
            'campo_ck': campo_ck,
            'ck': getattr(estudo, campo_ck, False),
            'am_str': am_str,
            'am_only': am_only,
        }
    return [
        tx('V.P.',                    'tx_vp',             'tx_vp_ck'),
        tx('Securitização',           'tx_securitizacao',  'tx_securitizacao_ck'),
        tx('Financiamento - Cliente', 'tx_financ_cliente', 'tx_financ_cliente_ck', am_only=True),
        tx('Financiamento - à Produção', 'tx_financ_producao', 'tx_financ_producao_ck'),
        tx('Capital Próprio',         'capital_proprio',   'capital_proprio_ck'),
    ]


def _agrupamentos_valor(estudo):
    from collections import defaultdict
    totais = defaultdict(lambda: {'qtde': 0, 'valor': 0.0})
    tipo_preco = estudo.tipo_preco_venda
    for c in estudo.configuracoes.select_related('agrupamento').all():
        ag = c.agrupamento.descricao if c.agrupamento else '—'
        qtde = c.config_qtde_total
        vlr  = float(c.config_valor_m2)
        if c.config_fechado:
            valor_und = vlr
        elif tipo_preco == 2:
            valor_und = float(c.config_area_priv) * vlr
        else:
            valor_und = float(c.config_area_real) * vlr
        totais[ag]['qtde']  += qtde
        totais[ag]['valor'] += valor_und * qtde
    return [(ag, v['qtde'], v['valor']) for ag, v in totais.items()]


def _context_painel(estudo):
    precos_sim = [
        ('1', 'simulacao_preco01_m2', estudo.simulacao_preco01_m2),
        ('2', 'simulacao_preco02_m2', estudo.simulacao_preco02_m2),
        ('3', 'simulacao_preco03_m2', estudo.simulacao_preco03_m2),
        ('4', 'simulacao_preco04_m2', estudo.simulacao_preco04_m2),
    ]
    return {
        'estudo': estudo,
        'empreendimentos': Empreendimento.objects.all(),
        'configs': estudo.configuracoes.select_related('tipo', 'agrupamento').all(),
        'agrupamentos': estudo.agrupamentos.all(),
        'velocidades': estudo.velocidades.select_related('agrupamento', 'param_vendas').all(),
        'construcoes': estudo.construcoes.select_related('curva').all(),
        'distribuicoes': estudo.distribuicoes.select_related('custo').all(),
        'params_vendas': estudo.params_vendas.all(),
        'curvas': Curva.objects.all(),
        'tipos': Tipo.objects.all(),
        'custos': Custo.objects.all(),
        'resumo': _resumo_calcular(estudo),
        'precos_sim': precos_sim,
        'periodos': _periodos(estudo),
        'agrupamentos_valor': _agrupamentos_valor(estudo),
        'taxas_financeiras': _taxas_financeiras(estudo),
    }


# ---------------------------------------------------------------------------
# Painel principal
# ---------------------------------------------------------------------------

class EstudoPainelView(LoginRequiredMixin, View):
    template_name = 'viabilidade/estudo/painel.html'

    def get(self, request, pk):
        estudo = get_object_or_404(Estudo, pk=pk)
        ctx = _context_painel(estudo)
        ctx['aba_ativa'] = request.GET.get('aba', 'receita')
        return render(request, self.template_name, ctx)

    def post(self, request, pk):
        estudo = get_object_or_404(Estudo, pk=pk)
        fields = [
            'planilha', 'dt_base', 'empreendimento',
            # Receita
            'tipo_preco_venda', 'area_real_total', 'area_priv_total',
            'simulacao_preco01_m2', 'simulacao_preco02_m2',
            'simulacao_preco03_m2', 'simulacao_preco04_m2',
            'receita_final',
            'investidor_partic', 'margem_negocial',
            # Construção
            'inicio_construcao', 'tempo_construcao', 'pre_lancamento', 'lancamento',
            'custo_m2_valor', 'custo_m2_tipo', 'area_equivalente_perc',
            'indice_reajuste', 'valor_cub',
            # Custos percentuais
            'perc_projetos', 'projetos_ck',
            'perc_itbi', 'itbi_ck',
            'perc_despesas', 'despesas_ck',
            'perc_marketing', 'marketing_ck',
            'perc_corretagem', 'corretagem_ck',
            'perc_impostos', 'impostos_ck',
            'perc_tx_adm', 'tx_adm_ck',
            'perc_assistencia', 'assistencia_ck',
            # Custos fixos
            'projetos_valor', 'indice_construcao', 'indice_ck',
            'tx_adm_area_constr_ck', 'custo_adm_exclusao',
            # Terreno
            'terreno_area', 'terreno_valor', 'cu_terreno_valor',
            'terreno_desemb_ck',
            'cu_terreno_cor', 'terreno_cor_ck',
            'terreno_valor_base_itbi',
            'terreneiro_invest', 'terreneiro_valor_m2',
            # Permuta
            'area_permutada', 'permu_fin_perc_receita',
            'permu_fin_perc_comissao', 'permu_fin_perc_marketing',
            # Financiamento
            'tx_vp', 'tx_vp_ck',
            'tx_securitizacao', 'tx_securitizacao_ck',
            'tx_financ_cliente', 'tx_financ_cliente_ck',
            'tx_financ_producao', 'tx_financ_producao_ck',
            'tx_cap_giro', 'tx_cap_giro_ck',
            'capital_proprio', 'capital_proprio_ck',
            'financ_prod_perc_construido', 'financ_prod_perc_vendido',
            'financ_prod_perc_financiamento',
            'financ_prod_carencia', 'financ_prod_qtde_parcelas',
        ]
        bool_fields = {
            f for f in fields
            if f.endswith('_ck') or f in ('receita_final', 'custo_adm_exclusao')
        }
        int_fields = {
            'tipo_preco_venda', 'custo_m2_tipo',
            'inicio_construcao', 'tempo_construcao', 'pre_lancamento', 'lancamento',
            'financ_prod_carencia', 'financ_prod_qtde_parcelas',
        }
        str_fields = {'dt_base', 'planilha'}
        p = request.POST



        try:
            from django.core.exceptions import ValidationError as DjValidationError
            emp_pk = p.get('empreendimento')
            if emp_pk:
                estudo.empreendimento_id = int(emp_pk)

            for f in fields:
                if f == 'empreendimento':
                    continue
                raw = p.get(f, '')
                if f in bool_fields:
                    setattr(estudo, f, f in p)
                elif f in int_fields:
                    setattr(estudo, f, int(raw) if raw else 0)
                elif f in str_fields:
                    setattr(estudo, f, raw.strip())
                else:
                    setattr(estudo, f, parse_decimal(raw))

            estudo.full_clean(exclude=['empreendimento'])
            estudo.save()
            messages.success(request, 'Estudo salvo com sucesso.')
            aba = p.get('aba_ativa', 'receita')
            return redirect(f"{reverse('viabilidade:estudo_painel', kwargs={'pk': pk})}?aba={aba}")
        except DjValidationError as e:
            msgs = '; '.join(
                f'{field}: {", ".join(errs)}' for field, errs in e.message_dict.items()
            ) if hasattr(e, 'message_dict') else str(e)
            messages.error(request, f'Valor inválido: {msgs}')
        except Exception as e:
            messages.error(request, f'Erro ao salvar: {e}')

        ctx = _context_painel(estudo)
        ctx['aba_ativa'] = p.get('aba_ativa', 'receita')
        return render(request, self.template_name, ctx)


# ---------------------------------------------------------------------------
# Cálculo AJAX (tempo real)
# ---------------------------------------------------------------------------

@login_required
def estudo_calcular_ajax(request, pk):
    estudo = get_object_or_404(Estudo, pk=pk)
    return JsonResponse(_resumo_calcular(estudo))


# ---------------------------------------------------------------------------
# HTMX — Config
# ---------------------------------------------------------------------------

def _render_config_table(request, estudo):
    return _render_htmx(request, 'viabilidade/htmx/config_table.html',
        estudo=estudo,
        configs=estudo.configuracoes.select_related('tipo', 'agrupamento').all(),
        tipos=Tipo.objects.all(),
        agrupamentos=estudo.agrupamentos.all(),
    )


@login_required
def htmx_config_table(request, estudo_pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    return _render_config_table(request, estudo)


@login_required
def htmx_config_form(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Config, pk=pk, estudo=estudo) if pk else None
    ctx = {
        'estudo': estudo, 'obj': obj,
        'tipos': Tipo.objects.all(),
        'agrupamentos': estudo.agrupamentos.all(),
    }
    return HttpResponse(render_to_string('viabilidade/htmx/config_form.html', ctx, request=request))


@login_required
def htmx_config_save(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Config, pk=pk, estudo=estudo) if pk else Config(estudo=estudo)
    p = request.POST

    dec = parse_decimal

    tipo_id = p.get('tipo')
    agrup_id = p.get('agrupamento')
    obj.tipo_id = int(tipo_id) if tipo_id else None
    obj.agrupamento_id = int(agrup_id) if agrup_id else None
    obj.config_qtde_total = int(p.get('config_qtde_total') or 0)
    obj.config_qtde_permu = int(p.get('config_qtde_permu') or 0)
    obj.config_qtde_imob = int(p.get('config_qtde_imob') or 0)
    obj.config_area_real = dec(p.get('config_area_real', ''))
    obj.config_area_priv = dec(p.get('config_area_priv', ''))
    obj.config_valor_m2 = dec(p.get('config_valor_m2', ''))
    obj.config_fechado = 'config_fechado' in p
    obj.config_ge = 'config_ge' in p
    obj.save()

    resp = _render_config_table(request, estudo)
    resp['HX-Trigger'] = 'configSaved'
    return resp


@login_required
def htmx_config_delete(request, estudo_pk, pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    get_object_or_404(Config, pk=pk, estudo=estudo).delete()
    return _render_config_table(request, estudo)


# ---------------------------------------------------------------------------
# HTMX — Velocidade
# ---------------------------------------------------------------------------

def _render_veloc_table(request, estudo):
    return _render_htmx(request, 'viabilidade/htmx/veloc_table.html',
        estudo=estudo,
        velocidades=estudo.velocidades.select_related('agrupamento', 'param_vendas').all(),
        agrupamentos=estudo.agrupamentos.all(),
        params_vendas=estudo.params_vendas.all(),
    )


@login_required
def htmx_veloc_table(request, estudo_pk):
    return _render_veloc_table(request, get_object_or_404(Estudo, pk=estudo_pk))


@login_required
def htmx_veloc_form(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Velocidade, pk=pk, estudo=estudo) if pk else None
    ctx = {
        'estudo': estudo, 'obj': obj,
        'agrupamentos': estudo.agrupamentos.all(),
        'params_vendas': estudo.params_vendas.all(),
    }
    return HttpResponse(render_to_string('viabilidade/htmx/veloc_form.html', ctx, request=request))


@login_required
def htmx_veloc_save(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Velocidade, pk=pk, estudo=estudo) if pk else Velocidade(estudo=estudo)
    p = request.POST

    dec = parse_decimal

    agrup_id = p.get('agrupamento')
    param_id = p.get('param_vendas')
    obj.agrupamento_id = int(agrup_id) if agrup_id else None
    obj.param_vendas_id = int(param_id) if param_id else None
    obj.veloc_perc = dec(p.get('veloc_perc', ''))
    obj.veloc_qtde = int(p.get('veloc_qtde') or 0)
    obj.veloc_inicio = int(p.get('veloc_inicio') or 0)
    obj.save()

    resp = _render_veloc_table(request, estudo)
    resp['HX-Trigger'] = 'velocSaved'
    return resp


@login_required
def htmx_veloc_delete(request, estudo_pk, pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    get_object_or_404(Velocidade, pk=pk, estudo=estudo).delete()
    return _render_veloc_table(request, estudo)


# ---------------------------------------------------------------------------
# HTMX — Construção
# ---------------------------------------------------------------------------

def _render_constru_table(request, estudo):
    return _render_htmx(request, 'viabilidade/htmx/constru_table.html',
        estudo=estudo,
        construcoes=estudo.construcoes.select_related('curva').all(),
        curvas=Curva.objects.all(),
    )


@login_required
def htmx_constru_table(request, estudo_pk):
    return _render_constru_table(request, get_object_or_404(Estudo, pk=estudo_pk))


@login_required
def htmx_constru_form(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Construcao, pk=pk, estudo=estudo) if pk else None
    ctx = {'estudo': estudo, 'obj': obj, 'curvas': Curva.objects.all()}
    return HttpResponse(render_to_string('viabilidade/htmx/constru_form.html', ctx, request=request))


@login_required
def htmx_constru_save(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Construcao, pk=pk, estudo=estudo) if pk else Construcao(estudo=estudo)
    p = request.POST

    dec = parse_decimal

    curva_id = p.get('curva')
    obj.curva_id = int(curva_id) if curva_id else None
    obj.descricao = p.get('descricao', '')
    obj.constru_perc = dec(p.get('constru_perc', ''))
    obj.constru_inicio = int(p.get('constru_inicio') or 0)
    obj.custo_m2 = dec(p.get('custo_m2', ''))
    obj.save()

    resp = _render_constru_table(request, estudo)
    resp['HX-Trigger'] = 'construSaved'
    return resp


@login_required
def htmx_constru_delete(request, estudo_pk, pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    get_object_or_404(Construcao, pk=pk, estudo=estudo).delete()
    return _render_constru_table(request, estudo)


# ---------------------------------------------------------------------------
# HTMX — Distribuição de Custos
# ---------------------------------------------------------------------------

def _render_distrib_table(request, estudo):
    return _render_htmx(request, 'viabilidade/htmx/distrib_table.html',
        estudo=estudo,
        distribuicoes=estudo.distribuicoes.select_related('custo').all(),
        custos=Custo.objects.all(),
    )


@login_required
def htmx_distrib_table(request, estudo_pk):
    return _render_distrib_table(request, get_object_or_404(Estudo, pk=estudo_pk))


@login_required
def htmx_distrib_form(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Distribuicao, pk=pk, estudo=estudo) if pk else None
    ctx = {'estudo': estudo, 'obj': obj, 'custos': Custo.objects.all()}
    return HttpResponse(render_to_string('viabilidade/htmx/distrib_form.html', ctx, request=request))


@login_required
def htmx_distrib_save(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(Distribuicao, pk=pk, estudo=estudo) if pk else Distribuicao(estudo=estudo)
    p = request.POST

    dec = parse_decimal

    custo_id = p.get('custo')
    obj.custo_id = int(custo_id) if custo_id else None
    obj.custo_perc = dec(p.get('custo_perc', ''))
    obj.custo_qtde = int(p.get('custo_qtde') or 1)
    obj.custo_inicio = int(p.get('custo_inicio') or 0)
    obj.save()

    resp = _render_distrib_table(request, estudo)
    resp['HX-Trigger'] = 'distribSaved'
    return resp


@login_required
def htmx_distrib_delete(request, estudo_pk, pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    get_object_or_404(Distribuicao, pk=pk, estudo=estudo).delete()
    return _render_distrib_table(request, estudo)


# ---------------------------------------------------------------------------
# HTMX — Parâmetros de Venda
# ---------------------------------------------------------------------------

def _render_param_table(request, estudo):
    return _render_htmx(request, 'viabilidade/htmx/param_table.html',
        estudo=estudo,
        params_vendas=estudo.params_vendas.all(),
    )


@login_required
def htmx_param_table(request, estudo_pk):
    return _render_param_table(request, get_object_or_404(Estudo, pk=estudo_pk))


@login_required
def htmx_param_form(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(ParamVendas, pk=pk, estudo=estudo) if pk else None
    return HttpResponse(render_to_string(
        'viabilidade/htmx/param_form.html', {'estudo': estudo, 'obj': obj}, request=request
    ))


@login_required
def htmx_param_save(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(ParamVendas, pk=pk, estudo=estudo) if pk else ParamVendas(estudo=estudo)
    p = request.POST

    dec = parse_decimal

    obj.descricao = p.get('descricao', '')
    obj.referencia = p.get('referencia', '')
    obj.tipo_financiamento = int(p.get('tipo_financiamento') or 1)
    obj.preco_venda_ref = int(p.get('preco_venda_ref') or 1)
    for f in ['ato_perc', 'parc_perc', 'ref_perc', 'cha_perc', 'fin_parc_perc', 'fin_ref_perc']:
        setattr(obj, f, dec(p.get(f, '')))
    for f in ['ato_qtde', 'parc_qtde', 'parc_apos', 'ref_qtde', 'ref_interv',
              'cha_apos', 'fin_parc_qtde', 'fin_parc_apos', 'fin_ref_qtde', 'fin_ref_interv']:
        setattr(obj, f, int(p.get(f) or 0))
    obj.save()

    resp = _render_param_table(request, estudo)
    resp['HX-Trigger'] = 'paramSaved'
    return resp


@login_required
def htmx_param_delete(request, estudo_pk, pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    get_object_or_404(ParamVendas, pk=pk, estudo=estudo).delete()
    return _render_param_table(request, estudo)


# ---------------------------------------------------------------------------
# HTMX — Agrupamentos
# ---------------------------------------------------------------------------

def _render_agrup_modal(request, estudo):
    return _render_htmx(request, 'viabilidade/htmx/agrup_modal.html',
        estudo=estudo,
        agrupamentos=estudo.agrupamentos.all(),
    )


@login_required
def htmx_agrup_table(request, estudo_pk):
    return _render_agrup_modal(request, get_object_or_404(Estudo, pk=estudo_pk))


@login_required
def htmx_agrup_form(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(ConfigAgrupamento, pk=pk, estudo=estudo) if pk else None
    html = render_to_string('viabilidade/htmx/agrup_modal.html', {
        'estudo': estudo,
        'agrupamentos': estudo.agrupamentos.all(),
        'obj': obj,
    }, request=request)
    return HttpResponse(html)


@login_required
def htmx_agrup_save(request, estudo_pk, pk=None):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    obj = get_object_or_404(ConfigAgrupamento, pk=pk, estudo=estudo) if pk else ConfigAgrupamento(estudo=estudo)
    obj.descricao = request.POST.get('descricao', '')
    obj.ordem = int(request.POST.get('ordem') or 0)
    obj.save()
    return _render_agrup_modal(request, estudo)


@login_required
def htmx_agrup_delete(request, estudo_pk, pk):
    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    get_object_or_404(ConfigAgrupamento, pk=pk, estudo=estudo).delete()
    return _render_agrup_modal(request, estudo)


# ---------------------------------------------------------------------------
# HTMX — Tipos (catálogo global, sem estudo_pk)
# ---------------------------------------------------------------------------

def _render_tipo_modal(request):
    return _render_htmx(request, 'viabilidade/htmx/tipo_modal.html',
        tipos=Tipo.objects.all(),
    )


# ---------------------------------------------------------------------------
# HTMX — Custos (catálogo global)
# ---------------------------------------------------------------------------

def _render_custo_modal(request):
    return _render_htmx(request, 'viabilidade/htmx/custo_modal.html',
        custos=Custo.objects.all(),
    )


@login_required
def htmx_custo_modal(request):
    return _render_custo_modal(request)


@login_required
def htmx_custo_save(request):
    descricao = request.POST.get('descricao', '').strip()
    if descricao:
        Custo.objects.create(
            descricao=descricao,
            distrib='distrib' in request.POST,
        )
    return _render_custo_modal(request)


@login_required
def htmx_custo_delete(request, pk):
    get_object_or_404(Custo, pk=pk).delete()
    return _render_custo_modal(request)


# ---------------------------------------------------------------------------
# HTMX — Curvas (catálogo global)
# ---------------------------------------------------------------------------

def _render_curva_modal(request):
    return _render_htmx(request, 'viabilidade/htmx/curva_modal.html',
        curvas=Curva.objects.all(),
    )


def _render_curva_meses(request, curva):
    meses = curva.meses.all()
    total = sum(float(m.curva_perc) for m in meses)
    html = render_to_string('viabilidade/htmx/curva_meses_modal.html', {
        'curva': curva,
        'meses': meses,
        'total_perc': round(total, 2),
    }, request=request)
    return HttpResponse(html)


@login_required
def htmx_curva_modal(request):
    return _render_curva_modal(request)


@login_required
def htmx_curva_save(request, pk=None):
    obj = get_object_or_404(Curva, pk=pk) if pk else Curva()
    obj.descricao = request.POST.get('descricao', '').strip()
    if obj.descricao:
        obj.save()
    return _render_curva_modal(request)


@login_required
def htmx_curva_delete(request, pk):
    get_object_or_404(Curva, pk=pk).delete()
    return _render_curva_modal(request)


@login_required
def htmx_curva_meses(request, curva_pk):
    return _render_curva_meses(request, get_object_or_404(Curva, pk=curva_pk))


@login_required
def htmx_curvames_save(request, curva_pk):
    curva = get_object_or_404(Curva, pk=curva_pk)
    mes = int(request.POST.get('curva_mes') or 0)
    raw = request.POST.get('curva_perc', '')
    val = raw.replace('.', '').replace(',', '.') if ',' in raw else raw
    try:
        perc = Decimal(val)
    except Exception:
        perc = Decimal('0')
    if mes >= 0:
        obj, _ = CurvaMes.objects.get_or_create(curva=curva, curva_mes=mes)
        obj.curva_perc = perc
        obj.save()
    return _render_curva_meses(request, curva)


@login_required
def htmx_curvames_delete(request, curva_pk, pk):
    curva = get_object_or_404(Curva, pk=curva_pk)
    get_object_or_404(CurvaMes, pk=pk, curva=curva).delete()
    return _render_curva_meses(request, curva)


# ---------------------------------------------------------------------------
# HTMX — Tipos (catálogo global)
# ---------------------------------------------------------------------------

@login_required
def htmx_tipo_modal(request):
    return _render_tipo_modal(request)


@login_required
def htmx_tipo_form(request, pk=None):
    obj = get_object_or_404(Tipo, pk=pk) if pk else None
    html = render_to_string('viabilidade/htmx/tipo_form.html', {
        'obj': obj,
    }, request=request)
    return HttpResponse(html)


@login_required
def htmx_tipo_save(request, pk=None):
    obj = get_object_or_404(Tipo, pk=pk) if pk else Tipo()
    obj.descricao = request.POST.get('descricao', '').strip()
    if obj.descricao:
        obj.save()
    return _render_tipo_modal(request)


@login_required
def htmx_tipo_delete(request, pk):
    get_object_or_404(Tipo, pk=pk).delete()
    return _render_tipo_modal(request)


# ---------------------------------------------------------------------------
# HTMX — Fluxo mensal por custo individual
# ---------------------------------------------------------------------------

_CUSTO_KEY_MAP = {
    'construcao':     ('Custo de Construção',                    2),
    'projetos':       ('Projetos / Aprovação',                   3),
    'terreno_desemb': ('Terreno (Desembolso Líquido)',           10),
    'terreno_cor':    ('Terreno (Corretagem)',                   11),
    'terreno_itbi':   ('Terreno (ITBI)',                          9),
    'indice':         ('Índice de Construção / Solo Criado',     12),
    'despesas':       ('Despesas Diversas',                      13),
    'marketing':      ('Marketing',                               6),
    'corretagem':     ('Corretagem sobre Unidades',               7),
    'impostos':       ('Impostos Federais (Lucro Presumido)',      8),
    'assistencia':    ('Assistência Técnica',                     5),
    'tx_adm':         ('Taxa de Administração',                   4),
}


@login_required
def htmx_custo_fluxo(request, estudo_pk, custo_key):
    if custo_key not in _CUSTO_KEY_MAP:
        return HttpResponse('Custo não encontrado', status=404)

    estudo = get_object_or_404(Estudo, pk=estudo_pk)
    calc = CalculadorViabilidade(estudo).calcular()
    label, linha_idx = _CUSTO_KEY_MAP[custo_key]

    rows = []
    total = 0.0
    for mes in range(calc.tamanho_ff):
        val = calc.fluxo[linha_idx][mes].valor
        if val:
            rows.append({
                'mes': mes,
                'referencia': calc.fluxo[0][mes].mex,
                'valor': val,
            })
            total += val

    return _render_htmx(request, 'viabilidade/htmx/custo_fluxo.html',
        label=label,
        rows=rows,
        total=total,
    )
