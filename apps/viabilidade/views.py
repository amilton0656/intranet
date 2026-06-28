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
