from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, View,
)
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count

from .models import (
    Empreendimento, Estudo, Config, Velocidade, Construcao,
    Distribuicao, ParamVendas, Curva, CurvaMes, Tipo, ConfigAgrupamento,
)
from .forms import (
    EmpreendimentoForm, EstudoForm, ConfigForm, VelocidadeForm,
    ConstrucaoForm, ParamVendasForm, CurvaForm, CurvaMesForm, TipoForm,
)
from .calculos import CalculadorViabilidade


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------

@login_required
def dashboard(request):
    context = {
        'total_empreendimentos': Empreendimento.objects.count(),
        'total_estudos': Estudo.objects.count(),
        'ultimos_estudos': Estudo.objects.select_related('empreendimento').order_by('-atualizado_em')[:5],
    }
    return render(request, 'viabilidade/dashboard.html', context)


# ------------------------------------------------------------------
# Empreendimentos
# ------------------------------------------------------------------

class EmpreendimentoListView(LoginRequiredMixin, ListView):
    model = Empreendimento
    template_name = 'viabilidade/empreendimento/list.html'
    context_object_name = 'empreendimentos'

    def get_queryset(self):
        return Empreendimento.objects.annotate(num_estudos=Count('estudos'))


class EmpreendimentoCreateView(LoginRequiredMixin, CreateView):
    model = Empreendimento
    form_class = EmpreendimentoForm
    template_name = 'viabilidade/empreendimento/form.html'
    success_url = reverse_lazy('viabilidade:empreendimento_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Novo Empreendimento'
        return ctx


class EmpreendimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Empreendimento
    form_class = EmpreendimentoForm
    template_name = 'viabilidade/empreendimento/form.html'
    success_url = reverse_lazy('viabilidade:empreendimento_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar: {self.object.nome}'
        return ctx


class EmpreendimentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Empreendimento
    template_name = 'viabilidade/confirm_delete.html'
    success_url = reverse_lazy('viabilidade:empreendimento_list')

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.pode_excluir():
            messages.error(request, 'Não é possível excluir: existem estudos vinculados.')
            return redirect('viabilidade:empreendimento_list')
        return super().post(request, *args, **kwargs)


# ------------------------------------------------------------------
# Estudos
# ------------------------------------------------------------------

class EstudoListView(LoginRequiredMixin, ListView):
    model = Estudo
    template_name = 'viabilidade/estudo/list.html'
    context_object_name = 'estudos'

    def get_queryset(self):
        return Estudo.objects.select_related('empreendimento').order_by(
            'empreendimento__nome', 'planilha'
        )


class EstudoCreateView(LoginRequiredMixin, CreateView):
    model = Estudo
    form_class = EstudoForm
    template_name = 'viabilidade/estudo/form.html'

    def get_success_url(self):
        return reverse('viabilidade:estudo_painel', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Novo Estudo'
        return ctx


class EstudoUpdateView(LoginRequiredMixin, UpdateView):
    model = Estudo
    form_class = EstudoForm
    template_name = 'viabilidade/estudo/form.html'

    def get_success_url(self):
        return reverse('viabilidade:estudo_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = f'Editar: {self.object}'
        return ctx


class EstudoDetailView(LoginRequiredMixin, DetailView):
    model = Estudo
    template_name = 'viabilidade/estudo/detail.html'
    context_object_name = 'estudo'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        estudo = self.object
        ctx['configs'] = estudo.configuracoes.select_related('tipo').all()
        ctx['velocidades'] = estudo.velocidades.all()
        ctx['construcoes'] = estudo.construcoes.select_related('curva').all()
        ctx['params_vendas'] = estudo.params_vendas.all()
        return ctx


class EstudoDeleteView(LoginRequiredMixin, DeleteView):
    model = Estudo
    template_name = 'viabilidade/confirm_delete.html'
    success_url = reverse_lazy('viabilidade:estudo_list')


class EstudoResultadoView(LoginRequiredMixin, View):
    template_name = 'viabilidade/estudo/resultado.html'

    def get(self, request, pk):
        estudo = get_object_or_404(Estudo, pk=pk)
        calc = CalculadorViabilidade(estudo).calcular()
        return render(request, self.template_name, {
            'estudo': estudo,
            'resumo': calc.resumo(),
        })


class EstudoFluxoView(LoginRequiredMixin, View):
    template_name = 'viabilidade/estudo/fluxo.html'

    def get(self, request, pk):
        estudo = get_object_or_404(Estudo, pk=pk)
        calc = CalculadorViabilidade(estudo).calcular()
        return render(request, self.template_name, {
            'estudo': estudo,
            'fluxo': calc.fluxo_mensal(),
            'resumo': calc.resumo(),
        })


# ------------------------------------------------------------------
# Mixin para views que dependem de um Estudo pai
# ------------------------------------------------------------------

class EstudoFilhoMixin:
    estudo_pk_url_kwarg = 'estudo_pk'

    def get_estudo(self):
        return get_object_or_404(Estudo, pk=self.kwargs[self.estudo_pk_url_kwarg])

    def get_queryset(self):
        return super().get_queryset().filter(estudo=self.get_estudo())

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estudo'] = self.get_estudo()
        return ctx

    def form_valid(self, form):
        form.instance.estudo = self.get_estudo()
        return super().form_valid(form)


# ------------------------------------------------------------------
# Configurações de Unidades
# ------------------------------------------------------------------

class ConfigListView(LoginRequiredMixin, EstudoFilhoMixin, ListView):
    model = Config
    template_name = 'viabilidade/config/list.html'
    context_object_name = 'configs'


class ConfigCreateView(LoginRequiredMixin, EstudoFilhoMixin, CreateView):
    model = Config
    form_class = ConfigForm
    template_name = 'viabilidade/config/form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['estudo'] = self.get_estudo()
        return kw

    def get_success_url(self):
        return reverse('viabilidade:config_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['titulo'] = 'Nova Configuração'
        return ctx


class ConfigUpdateView(LoginRequiredMixin, EstudoFilhoMixin, UpdateView):
    model = Config
    form_class = ConfigForm
    template_name = 'viabilidade/config/form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['estudo'] = self.get_estudo()
        return kw

    def get_success_url(self):
        return reverse('viabilidade:config_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class ConfigDeleteView(LoginRequiredMixin, EstudoFilhoMixin, DeleteView):
    model = Config
    template_name = 'viabilidade/confirm_delete.html'

    def get_success_url(self):
        return reverse('viabilidade:config_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


# ------------------------------------------------------------------
# Velocidade de Vendas
# ------------------------------------------------------------------

class VelocidadeListView(LoginRequiredMixin, EstudoFilhoMixin, ListView):
    model = Velocidade
    template_name = 'viabilidade/velocidade/list.html'
    context_object_name = 'velocidades'


class VelocidadeCreateView(LoginRequiredMixin, EstudoFilhoMixin, CreateView):
    model = Velocidade
    form_class = VelocidadeForm
    template_name = 'viabilidade/velocidade/form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['estudo'] = self.get_estudo()
        return kw

    def get_success_url(self):
        return reverse('viabilidade:velocidade_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class VelocidadeUpdateView(LoginRequiredMixin, EstudoFilhoMixin, UpdateView):
    model = Velocidade
    form_class = VelocidadeForm
    template_name = 'viabilidade/velocidade/form.html'

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw['estudo'] = self.get_estudo()
        return kw

    def get_success_url(self):
        return reverse('viabilidade:velocidade_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class VelocidadeDeleteView(LoginRequiredMixin, EstudoFilhoMixin, DeleteView):
    model = Velocidade
    template_name = 'viabilidade/confirm_delete.html'

    def get_success_url(self):
        return reverse('viabilidade:velocidade_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


# ------------------------------------------------------------------
# Construção
# ------------------------------------------------------------------

class ConstrucaoListView(LoginRequiredMixin, EstudoFilhoMixin, ListView):
    model = Construcao
    template_name = 'viabilidade/construcao/list.html'
    context_object_name = 'construcoes'


class ConstrucaoCreateView(LoginRequiredMixin, EstudoFilhoMixin, CreateView):
    model = Construcao
    form_class = ConstrucaoForm
    template_name = 'viabilidade/construcao/form.html'

    def get_success_url(self):
        return reverse('viabilidade:construcao_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class ConstrucaoUpdateView(LoginRequiredMixin, EstudoFilhoMixin, UpdateView):
    model = Construcao
    form_class = ConstrucaoForm
    template_name = 'viabilidade/construcao/form.html'

    def get_success_url(self):
        return reverse('viabilidade:construcao_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class ConstrucaoDeleteView(LoginRequiredMixin, EstudoFilhoMixin, DeleteView):
    model = Construcao
    template_name = 'viabilidade/confirm_delete.html'

    def get_success_url(self):
        return reverse('viabilidade:construcao_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


# ------------------------------------------------------------------
# Parâmetros de Venda
# ------------------------------------------------------------------

class ParamVendasListView(LoginRequiredMixin, EstudoFilhoMixin, ListView):
    model = ParamVendas
    template_name = 'viabilidade/paramvendas/list.html'
    context_object_name = 'params'


class ParamVendasCreateView(LoginRequiredMixin, EstudoFilhoMixin, CreateView):
    model = ParamVendas
    form_class = ParamVendasForm
    template_name = 'viabilidade/paramvendas/form.html'

    def get_success_url(self):
        return reverse('viabilidade:paramvendas_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class ParamVendasUpdateView(LoginRequiredMixin, EstudoFilhoMixin, UpdateView):
    model = ParamVendas
    form_class = ParamVendasForm
    template_name = 'viabilidade/paramvendas/form.html'

    def get_success_url(self):
        return reverse('viabilidade:paramvendas_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


class ParamVendasDeleteView(LoginRequiredMixin, EstudoFilhoMixin, DeleteView):
    model = ParamVendas
    template_name = 'viabilidade/confirm_delete.html'

    def get_success_url(self):
        return reverse('viabilidade:paramvendas_list', kwargs={'estudo_pk': self.kwargs['estudo_pk']})


# ------------------------------------------------------------------
# Curvas
# ------------------------------------------------------------------

class CurvaListView(LoginRequiredMixin, ListView):
    model = Curva
    template_name = 'viabilidade/curva/list.html'
    context_object_name = 'curvas'

    def get_queryset(self):
        return Curva.objects.annotate(num_meses=Count('meses'))


class CurvaCreateView(LoginRequiredMixin, CreateView):
    model = Curva
    form_class = CurvaForm
    template_name = 'viabilidade/curva/form.html'
    success_url = reverse_lazy('viabilidade:curva_list')


class CurvaUpdateView(LoginRequiredMixin, UpdateView):
    model = Curva
    form_class = CurvaForm
    template_name = 'viabilidade/curva/form.html'
    success_url = reverse_lazy('viabilidade:curva_list')


class CurvaDeleteView(LoginRequiredMixin, DeleteView):
    model = Curva
    template_name = 'viabilidade/confirm_delete.html'
    success_url = reverse_lazy('viabilidade:curva_list')


class CurvaMesListView(LoginRequiredMixin, ListView):
    model = CurvaMes
    template_name = 'viabilidade/curva/meses.html'
    context_object_name = 'meses'

    def get_queryset(self):
        return CurvaMes.objects.filter(curva_id=self.kwargs['curva_pk'])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['curva'] = get_object_or_404(Curva, pk=self.kwargs['curva_pk'])
        total = sum(float(m.curva_perc) for m in ctx['meses'])
        ctx['total_perc'] = round(total, 4)
        return ctx


class CurvaMesCreateView(LoginRequiredMixin, CreateView):
    model = CurvaMes
    form_class = CurvaMesForm
    template_name = 'viabilidade/curva/mes_form.html'

    def form_valid(self, form):
        form.instance.curva = get_object_or_404(Curva, pk=self.kwargs['curva_pk'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('viabilidade:curvames_list', kwargs={'curva_pk': self.kwargs['curva_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['curva'] = get_object_or_404(Curva, pk=self.kwargs['curva_pk'])
        return ctx


class CurvaMesUpdateView(LoginRequiredMixin, UpdateView):
    model = CurvaMes
    form_class = CurvaMesForm
    template_name = 'viabilidade/curva/mes_form.html'

    def get_success_url(self):
        return reverse('viabilidade:curvames_list', kwargs={'curva_pk': self.kwargs['curva_pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['curva'] = get_object_or_404(Curva, pk=self.kwargs['curva_pk'])
        return ctx


class CurvaMesDeleteView(LoginRequiredMixin, DeleteView):
    model = CurvaMes
    template_name = 'viabilidade/confirm_delete.html'

    def get_success_url(self):
        return reverse('viabilidade:curvames_list', kwargs={'curva_pk': self.kwargs['curva_pk']})


# ------------------------------------------------------------------
# Tipos
# ------------------------------------------------------------------

class TipoListView(LoginRequiredMixin, ListView):
    model = Tipo
    template_name = 'viabilidade/tipo/list.html'
    context_object_name = 'tipos'


class TipoCreateView(LoginRequiredMixin, CreateView):
    model = Tipo
    form_class = TipoForm
    template_name = 'viabilidade/tipo/form.html'
    success_url = reverse_lazy('viabilidade:tipo_list')


class TipoUpdateView(LoginRequiredMixin, UpdateView):
    model = Tipo
    form_class = TipoForm
    template_name = 'viabilidade/tipo/form.html'
    success_url = reverse_lazy('viabilidade:tipo_list')


class TipoDeleteView(LoginRequiredMixin, DeleteView):
    model = Tipo
    template_name = 'viabilidade/confirm_delete.html'
    success_url = reverse_lazy('viabilidade:tipo_list')


# ------------------------------------------------------------------
# Relatório PDF — Previsão de Resultados
# ------------------------------------------------------------------

@login_required
def exportar_resultado(request, pk):
    from django.http import HttpResponse
    estudo = get_object_or_404(
        Estudo.objects.select_related('empreendimento'), pk=pk
    )
    pdf_bytes = _build_resultado_pdf(estudo)
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = (
        f'inline; filename="resultado_{estudo.planilha}.pdf"'
    )
    return resp


def _build_resultado_pdf(estudo):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from io import BytesIO
    import datetime as dt

    from .calculos import CalculadorViabilidade, parse_dt_base, mes_para_str

    buf = BytesIO()
    MG = 10 * mm
    W_PAGE, _ = landscape(A4)
    W = W_PAGE - 2 * MG  # ≈ 257 mm

    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=MG, rightMargin=MG,
        topMargin=MG, bottomMargin=MG,
    )

    # ── Cálculo ─────────────────────────────────────────────────────────
    calc = CalculadorViabilidade(estudo).calcular()
    r    = calc.resumo()
    e    = estudo

    _MESES = ['JAN','FEV','MAR','ABR','MAI','JUN','JUL','AGO','SET','OUT','NOV','DEZ']

    def _dt_fmt(dt_base):
        if not dt_base or len(dt_base) != 6:
            return dt_base or '—'
        return f'{_MESES[int(dt_base[:2])-1]}/{dt_base[2:]}'

    def _off_fmt(offset):
        mb, ab = parse_dt_base(e.dt_base)
        s = mes_para_str(int(offset), mb, ab)
        return f'{_MESES[int(s[:2])-1]}/{s[3:]}'

    def _brl(v):
        if v is None:
            return '—'
        return 'R$ {:,.2f}'.format(float(v)).replace(',','X').replace('.',',').replace('X','.')

    def _n(v, d=2):
        return '{:,.{}f}'.format(float(v), d).replace(',','X').replace('.',',').replace('X','.')

    def _pct(v):
        return '{:,.2f}%'.format(float(v)).replace(',','X').replace('.',',').replace('X','.')

    # ── Cores ────────────────────────────────────────────────────────────
    C_HDR   = colors.HexColor('#1a3a5c')
    C_SEC   = colors.HexColor('#2d5986')
    C_SEC2  = colors.HexColor('#3a6ea5')
    C_LBLBG = colors.HexColor('#d9e1ea')
    C_SUBBG = colors.HexColor('#eef3f8')
    C_TOT   = colors.HexColor('#e8f5e9')
    C_LBRL  = colors.HexColor('#c8e6c9')
    C_WHITE = colors.white
    C_DGRAY = colors.HexColor('#444444')
    C_GRID  = colors.HexColor('#bbbbbb')
    C_IGRID = colors.HexColor('#dddddd')

    sty = getSampleStyleSheet()

    def ps(name, **kw):
        return ParagraphStyle(name, parent=sty['Normal'], **kw)

    def _p(txt, bold=False, size=7, color='#222222', align=0):
        fn = 'Helvetica-Bold' if bold else 'Helvetica'
        return Paragraph(
            f'<font name="{fn}" size="{size}" color="{color}">{txt}</font>',
            ps(f'p_{id(txt)}', alignment=align, leading=size + 2)
        )

    def _pc(txt, **kw):   return _p(txt, align=1, **kw)
    def _pr(txt, **kw):   return _p(txt, align=2, **kw)

    BASE_STYLE = [
        ('BOX',           (0,0), (-1,-1), 0.5, C_GRID),
        ('INNERGRID',     (0,0), (-1,-1), 0.3, C_IGRID),
        ('FONTSIZE',      (0,0), (-1,-1), 7),
        ('LEADING',       (0,0), (-1,-1), 9),
        ('TOPPADDING',    (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING',   (0,0), (-1,-1), 3),
        ('RIGHTPADDING',  (0,0), (-1,-1), 3),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]

    story = []

    # ══════════════════════════════════════════════════════════════════════
    # 1. CABEÇALHO
    # ══════════════════════════════════════════════════════════════════════
    now     = dt.datetime.now()
    ds      = ['Segunda-feira','Terça-feira','Quarta-feira','Quinta-feira',
               'Sexta-feira','Sábado','Domingo'][now.weekday()]
    dt_str  = f'{ds}, {now.strftime("%d de %B de %Y")} às {now.strftime("%H:%M")} h'

    hdr_data = [[
        _p('<b>COTA</b>  <font size="7">COTA Empreendimentos Imobiliários Ltda.</font>'
           '<br/><font size="7.5">Viabilidade - Previsão de Resultados</font>',
           size=10, color='#ffffff'),
        _pr(f'Data da Impressão :  {dt_str}', size=6.5, color='#ccddee'),
        _pr('Página :  1 / 1', size=6.5, color='#ccddee'),
    ]]
    t_hdr = Table(hdr_data, colWidths=[W*0.52, W*0.38, W*0.10])
    t_hdr.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), C_HDR),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (0,0), 8),
        ('BOX',           (0,0), (-1,-1), 0.7, colors.HexColor('#0a2040')),
    ]))
    story.append(t_hdr)

    # ══════════════════════════════════════════════════════════════════════
    # 2. IDENTIFICAÇÃO
    # ══════════════════════════════════════════════════════════════════════
    cw_id = [W*0.15, W*0.15, W*0.08, W*0.08, W*0.08, W*0.07,
             W*0.10, W*0.10, W*0.10, W*0.09]
    id_data = [
        [_p('Empreendimento',bold=True,size=6.5), _p('Descrição',bold=True,size=6.5),
         _p('Planilha',bold=True,size=6.5),
         _p('Pré-Lançamento',bold=True,size=6.5), _p('Lançamento',bold=True,size=6.5),
         _p('DataBase',bold=True,size=6.5),
         _pc('Diretor\nPresidente',size=6.5), _pc('Diretor\nComercial',size=6.5),
         _pc('Diretor\nOperacional',size=6.5), _pc('Diretor\nTécnico',size=6.5)],
        [_p(e.empreendimento.nome, bold=True), _p(e.empreendimento.descricao or ''),
         _p(e.planilha, bold=True),
         _pc(_off_fmt(e.pre_lancamento), bold=True), _pc(_off_fmt(e.lancamento), bold=True),
         _pc(_dt_fmt(e.dt_base), bold=True),
         _p(''), _p(''), _p(''), _p('')],
    ]
    t_id = Table(id_data, colWidths=cw_id)
    t_id.setStyle(TableStyle(BASE_STYLE + [
        ('BACKGROUND',    (0,0), (-1,0), C_LBLBG),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWHEIGHT',     (0,1), (-1,1), 14),
        ('BOX',           (6,0), (9,1), 0.5, C_GRID),
    ]))
    story.append(t_id)

    # ══════════════════════════════════════════════════════════════════════
    # 3. FÓRMULA DE EFICIÊNCIA — linha 1
    # ══════════════════════════════════════════════════════════════════════
    area_priv_media  = r['area_priv_media_unid']
    preco_medio_m2   = r['preco_medio_m2']
    preco_venda_unid = r['preco_medio_unid']
    und_avenda       = r['und_avenda']
    gar_total        = r['gar_total']
    rec_liq          = r['rec_liq']

    OP = W * 0.025   # coluna do operador (×, +, =)
    cw_f1 = [W*0.13, OP, W*0.12, OP, W*0.14, OP, W*0.09, OP, W*0.09, OP, W*0.165, W*0.135]
    f1_data = [
        [_pc('ÁreaPriv.Média(unid.)',size=6.5), _pc(''),
         _pc('Preço médio p/ m²',size=6.5),     _pc(''),
         _pc('Preço de Venda',size=6.5),         _pc(''),
         _pc('Unidades à Venda',size=6.5),       _pc(''),
         _pc('Vagas Extras',size=6.5),            _pc(''),
         _pc('Totais ($ juros)',size=6.5),        _pc('')],
        [_pc(f'{_n(area_priv_media,4)} m²',bold=True),
         _pc('×',bold=True,size=9),
         _pc(_brl(preco_medio_m2),bold=True),
         _pc('=',bold=True,size=9),
         _pc(_brl(preco_venda_unid),bold=True),
         _pc('+',bold=True,size=9),
         _pc(_n(und_avenda,2),bold=True),
         _pc('+',bold=True,size=9),
         _pc(_n(gar_total,2),bold=True),
         _pc('=',bold=True,size=9),
         _pc(_brl(rec_liq),bold=True,size=7.5,color='#1a3a5c'),
         _pc('')],
    ]
    t_f1 = Table(f1_data, colWidths=cw_f1)
    t_f1.setStyle(TableStyle(BASE_STYLE + [
        ('BACKGROUND', (0,0), (-1,0), C_SUBBG),
        ('NOSPLIT',    (0,0), (-1,-1)),
    ]))
    story.append(t_f1)

    # ══════════════════════════════════════════════════════════════════════
    # 4. FÓRMULA DE EFICIÊNCIA — linha 2 (Eficiência + Custo Construção)
    # ══════════════════════════════════════════════════════════════════════
    efic           = r['eficiencia_decimal']
    area_real_tot  = r['area_real_total']
    area_priv_tot  = r['area_priv_total']
    area_equiv     = r['area_equivalente']
    cm2_real       = r['custo_m2_real']
    cm2_priv       = r['custo_m2_priv']
    cm2_equiv      = r['custo_m2_equiv']
    tx_adm_pct     = float(e.perc_tx_adm)
    assist_pct     = float(e.perc_assistencia)

    custo_const_total = (
        r['custo_construcao']
        + (float(e.projetos_valor) if e.projetos_ck else 0)
        + r['cu_tx_adm']
        + r['cu_assistencia']
    )

    EL = W * 0.10    # coluna "Eficiência do Projeto"
    ER = W - EL

    # Sub-tabela direita: 3 linhas de área × custo_m2, com fórmula principal
    SC = [ER*0.22, ER*0.04, ER*0.17, ER*0.04, ER*0.13, ER*0.04, ER*0.13, ER*0.04, ER*0.19]

    ef_right_data = [
        # row 0: labels
        [_pc('Área Real Total',size=6.5),   _pc(''), _pc('Custo/m² (Real)',size=6.5),
         _pc(''), _pc('Tx Administração',size=6.5),
         _pc(''), _pc('Assistência Técnica',size=6.5),
         _pc('=',bold=True,size=9), _pc('Custo Total Construção',size=6.5)],
        # row 1: valores linha real
        [_pc(f'{_n(area_real_tot,2)} m²',bold=True),
         _pc('×',bold=True,size=9), _pc(_brl(cm2_real),bold=True),
         _pc('×',bold=True,size=9), _pc(_pct(tx_adm_pct),bold=True),
         _pc('+',bold=True,size=9), _pc(_pct(assist_pct),bold=True),
         _pc(''),
         _pc(_brl(custo_const_total),bold=True,size=7.5,color='#1a3a5c')],
        # row 2: labels linha privativa
        [_pc('Área Privativa Total',size=6.5), _pc(''), _pc('Custo/m² (Priv.)',size=6.5),
         _pc(''), _pc(''), _pc(''), _pc(''), _pc(''), _pc('')],
        # row 3: valores privativa
        [_pc(f'{_n(area_priv_tot,2)} m²',bold=True),
         _pc('×',bold=True,size=9), _pc(_brl(cm2_priv),bold=True),
         _pc(''), _pc(''), _pc(''), _pc(''), _pc(''), _pc('')],
        # row 4: labels equivalente
        [_pc('Área Total Equivalente',size=6.5), _pc(''), _pc('Custo/m² (Equiv.)',size=6.5),
         _pc(''), _pc(''), _pc(''), _pc(''), _pc(''), _pc('')],
        # row 5: valores equivalente
        [_pc(f'{_n(area_equiv,2)} m²',bold=True),
         _pc('×',bold=True,size=9), _pc(_brl(cm2_equiv),bold=True),
         _pc(''), _pc(''), _pc(''), _pc(''), _pc(''), _pc('')],
    ]
    t_ef_right = Table(ef_right_data, colWidths=SC)
    t_ef_right.setStyle(TableStyle([
        ('FONTSIZE',   (0,0), (-1,-1), 7),
        ('LEADING',    (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('LEFTPADDING',   (0,0), (-1,-1), 2),
        ('RIGHTPADDING',  (0,0), (-1,-1), 2),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), C_SUBBG),
        ('BACKGROUND', (0,2), (-1,2), C_SUBBG),
        ('BACKGROUND', (0,4), (-1,4), C_SUBBG),
        # Span custo total + = operator across all rows
        ('SPAN',       (7,0), (7,5)),
        ('SPAN',       (8,0), (8,5)),
        ('BOX',        (8,0), (8,5), 0.5, C_GRID),
        ('BOX',        (0,0), (-1,-1), 0.5, C_GRID),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, C_IGRID),
    ]))

    ef_left_data = [
        [_pc('Eficiência\ndo Projeto', bold=True, size=6.5)],
        [_pc(_n(efic,4), bold=True, size=11, color='#1a3a5c')],
        [_pc('')],
        [_pc('')],
        [_pc('')],
        [_pc('')],
    ]
    t_ef_left = Table(ef_left_data, colWidths=[EL])
    t_ef_left.setStyle(TableStyle([
        ('BOX',        (0,0), (-1,-1), 0.5, C_GRID),
        ('INNERGRID',  (0,0), (-1,-1), 0.3, C_IGRID),
        ('BACKGROUND', (0,0), (-1,-1), C_SUBBG),
        ('FONTSIZE',   (0,0), (-1,-1), 7),
        ('LEADING',    (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
        ('VALIGN',     (0,0), (0,0), 'TOP'),
        ('VALIGN',     (0,1), (0,1), 'MIDDLE'),
        ('SPAN',       (0,2), (0,5)),
    ]))

    t_ef = Table([[t_ef_left, t_ef_right]], colWidths=[EL, ER])
    t_ef.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('BOX',           (0,0), (-1,-1), 0.5, C_GRID),
    ]))
    story.append(t_ef)

    # ══════════════════════════════════════════════════════════════════════
    # 5. FORMA DE PERMUTA
    # ══════════════════════════════════════════════════════════════════════
    und_total  = r['und_total']
    und_permu  = r['und_permu']
    und_imob   = r['und_imob']
    cu_itbi    = r['cu_itbi']
    terreno_v  = float(e.terreno_valor)
    terreno_a  = float(e.terreno_area)
    terreno_m2 = float(e.terreneiro_valor_m2)

    custo_raso_avenda = (r['custo_construcao'] / und_avenda) if und_avenda else 0.0

    cw_pe = [W*0.08, W*0.07, W*0.07, W*0.10, W*0.10,
             W*0.13, W*0.13, W*0.12, W*0.20]

    pe_hdr = [
        _pc('Forma de\nPermuta',bold=True,size=6.5),
        _pc('Unidades',bold=True,size=6.5),
        _pc('V.G.Extras',bold=True,size=6.5),
        _pc('Área Real (m²)',bold=True,size=6.5),
        _pc('Área Privativa (m²)',bold=True,size=6.5),
        _pc('Custo Raso\nd/Unidade',bold=True,size=6.5),
        _pc('Terreno\nValor',bold=True,size=6.5),
        _pc('Área',bold=True,size=6.5),
        _pc('Preço/m²',bold=True,size=6.5),
    ]

    def pe_row(label, qtde, ge, area_r, area_p, custo_raso, terr_v, terr_a, terr_m2, bold=False):
        return [
            _p(label, bold=bold),
            _pc(_n(qtde,2),  bold=bold),
            _pc(_n(ge,2),    bold=bold),
            _pr(_n(area_r,2), bold=bold),
            _pr(_n(area_p,2), bold=bold),
            _pr(_brl(custo_raso), bold=bold),
            _pr(_brl(terr_v),  bold=bold),
            _pr(f'{_n(terr_a,2)} m²', bold=bold),
            _pr(_brl(terr_m2), bold=bold),
        ]

    pe_data = [
        pe_hdr,
        pe_row('Total',       und_total, gar_total, area_real_tot, area_priv_tot,
               terreno_v, terreno_v, terreno_a, terreno_m2, bold=True),
        pe_row('Permutadas',  und_permu, 0, 0, 0,   0, 0, 0, 0),
        pe_row('Imobilizadas',und_imob,  0, 0, 0,   0, 0, 0, 0),
        pe_row('À Venda',     und_avenda,0, area_real_tot, area_priv_tot,
               custo_raso_avenda, 0, 0, 0, bold=True),
    ]
    t_pe = Table(pe_data, colWidths=cw_pe)
    t_pe.setStyle(TableStyle(BASE_STYLE + [
        ('BACKGROUND',    (0,0), (-1,0), C_SEC),
        ('TEXTCOLOR',     (0,0), (-1,0), C_WHITE),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND',    (0,1), (-1,1), C_SUBBG),
        ('BACKGROUND',    (0,4), (-1,4), C_SUBBG),
    ]))
    story.append(t_pe)

    # ══════════════════════════════════════════════════════════════════════
    # 6. TABELA FINANCEIRA PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════
    custo_construcao  = r['custo_construcao']
    projetos_v        = float(e.projetos_valor) if e.projetos_ck else 0.0
    cu_tx_adm         = r['cu_tx_adm']
    cu_assistencia    = r['cu_assistencia']
    cu_marketing      = r['cu_marketing']
    cu_corretagem     = r['cu_corretagem']
    cu_impostos       = r['cu_impostos']
    cu_terreno_desemb = r['cu_terreno_desemb']
    cu_terreno_cor    = float(e.cu_terreno_cor) if e.terreno_cor_ck else 0.0
    cu_indice         = float(e.indice_construcao) if e.indice_ck else 0.0
    cu_despesas       = r['cu_despesas']
    custo_total       = r['custo_total']
    resultado_liq     = r['resultado_liq']
    margem_liq        = r['margem_liq']

    custo_const_grp   = custo_construcao + projetos_v + cu_tx_adm + cu_assistencia
    custo_desp_grp    = cu_marketing + cu_corretagem + cu_impostos
    custo_terr_grp    = cu_itbi + cu_terreno_desemb + cu_terreno_cor + cu_indice
    custo_outr_grp    = cu_despesas
    custo_fin_grp     = 0.0

    CL = W * 0.38  # label column
    CV = (W - CL) / 3  # 3 value columns

    cw_fin = [CL, CV, CV, CV]

    def _fr(label, v1, v2=None, v3=None, bold=False, indent=False, bg=None, tc=None):
        """Financial row: label + 3 value columns."""
        if v2 is None: v2 = v1
        if v3 is None: v3 = v2
        lbl = ('    ' if indent else '') + label
        return [
            _p(lbl, bold=bold),
            _pr(_brl(v1) if v1 != '' else '', bold=bold),
            _pr(_brl(v2) if v2 != '' else '', bold=bold),
            _pr(_brl(v3) if v3 != '' else '', bold=bold),
        ]

    fin_col_hdr = [
        _p('Itens', bold=True, size=6.5),
        _pc('Total a V.P. (R$)', bold=True, size=6.5),
        _pc('Total (R$)\n(Sem Juros Cliente)', bold=True, size=6.5),
        _pc('Total (R$)\n(Com Juros Cliente)', bold=True, size=6.5),
    ]

    # Seção helper
    def _sec(label):
        return [_p(label, bold=True, size=7, color='#ffffff'), _p(''), _p(''), _p('')]

    fin_rows = [
        fin_col_hdr,

        # Receitas
        _sec('(+) Receitas'),
        _fr('Receita Líquida', rec_liq, indent=True),
        _fr('Permutas', r['rec_permu'], indent=True),

        # Custo Construção
        _sec('(-) Custo Construção'),
        _fr('Construção', custo_construcao, indent=True),
        _fr('Projetos / Aprovação', projetos_v, indent=True),
        _fr('Taxa de Administração', cu_tx_adm, indent=True),
        _fr('Assistência Técnica', cu_assistencia, indent=True),

        # Despesas Comerciais
        _sec('(-) Despesas Comerciais e Marketing'),
        _fr('Marketing', cu_marketing, indent=True),
        _fr('Corretagem sobre Unidades', cu_corretagem, indent=True),
        _fr('Impostos Federais (Lucro Presumido)', cu_impostos, indent=True),

        # Terreno
        _sec('(-) Terreno'),
        _fr('Terreno (ITBI)', cu_itbi, indent=True),
        _fr('Terreno (Desembolso Líquido)', cu_terreno_desemb, indent=True),
        _fr('Terreno (Corretagem)', cu_terreno_cor, indent=True),
        _fr('Índices de Construção / Solo Criado', cu_indice, indent=True),

        # Outros
        _sec('(-) Outros'),
        _fr('Despesas Diversas', cu_despesas, indent=True),

        # Financeiro
        _sec('(-) Financeiro (Juros)'),
        _fr('Financiamento Produção - Juros', 0.0, indent=True),
        _fr('Capital Próprio - Juros', 0.0, indent=True),
        _fr('Investimento Máximo', 0.0, indent=True),
        _fr('Maior Investimento no Mês', 0.0, indent=True),

        # Totais
        _fr('(-) Custo Total', custo_total, bold=True),
        _fr('= Lucro Líquido', resultado_liq, bold=True),
        [_p('Lucro Líquido / Receita (%)', bold=True),
         _pr(_pct(margem_liq), bold=True),
         _pr(_pct(margem_liq), bold=True),
         _pr(_pct(margem_liq), bold=True)],
    ]

    # Índices das seções (para colorir)
    SEC_ROWS    = [1, 4, 9, 13, 18, 20]   # linhas de seção (0-based)
    TOT_ROWS    = [26, 27, 28]
    SUBTOT_ROWS = []

    t_fin = Table(fin_rows, colWidths=cw_fin)
    fin_style = list(BASE_STYLE)
    for i in SEC_ROWS:
        fin_style += [
            ('BACKGROUND', (0,i), (-1,i), C_SEC2),
            ('TEXTCOLOR',  (0,i), (-1,i), C_WHITE),
            ('FONTNAME',   (0,i), (-1,i), 'Helvetica-Bold'),
        ]
    for i in TOT_ROWS:
        fin_style += [
            ('BACKGROUND', (0,i), (-1,i), C_TOT if i < 28 else C_LBRL),
            ('FONTNAME',   (0,i), (-1,i), 'Helvetica-Bold'),
        ]
    fin_style += [
        ('BACKGROUND',  (0,0), (-1,0), C_SEC),
        ('TEXTCOLOR',   (0,0), (-1,0), C_WHITE),
        ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
        # Linha do cabeçalho mais alta
        ('ROWHEIGHT',   (0,0), (-1,0), 22),
        ('VALIGN',      (0,0), (-1,0), 'MIDDLE'),
    ]
    t_fin.setStyle(TableStyle(fin_style))
    story.append(t_fin)

    doc.build(story)
    return buf.getvalue()
