from django import forms
from .models import (
    Empreendimento, Estudo, Config, Velocidade, Construcao,
    Distribuicao, ParamVendas, Curva, CurvaMes, Tipo, ConfigAgrupamento,
)


class EmpreendimentoForm(forms.ModelForm):
    class Meta:
        model = Empreendimento
        fields = ['nome', 'descricao']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class EstudoForm(forms.ModelForm):
    class Meta:
        model = Estudo
        fields = ['empreendimento', 'planilha', 'dt_base']
        widgets = {
            'empreendimento': forms.Select(attrs={'class': 'form-select'}),
            'planilha': forms.TextInput(attrs={'class': 'form-control'}),
            'dt_base': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MMAAAA'}),
        }

    def clean_dt_base(self):
        val = self.cleaned_data.get('dt_base', '')
        if val and (len(val) != 6 or not val.isdigit()):
            raise forms.ValidationError('Formato deve ser MMAAAA (ex: 012024)')
        return val


class ConfigForm(forms.ModelForm):
    class Meta:
        model = Config
        exclude = ['estudo']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'agrupamento': forms.Select(attrs={'class': 'form-select'}),
            'config_qtde_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'config_qtde_permu': forms.NumberInput(attrs={'class': 'form-control'}),
            'config_qtde_imob': forms.NumberInput(attrs={'class': 'form-control'}),
            'config_area_real': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'config_area_priv': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'config_valor_m2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'config_fechado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'config_ge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, estudo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estudo:
            self.fields['agrupamento'].queryset = ConfigAgrupamento.objects.filter(estudo=estudo)


class VelocidadeForm(forms.ModelForm):
    class Meta:
        model = Velocidade
        exclude = ['estudo']
        widgets = {
            'agrupamento': forms.Select(attrs={'class': 'form-select'}),
            'param_vendas': forms.Select(attrs={'class': 'form-select'}),
            'veloc_perc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'veloc_qtde': forms.NumberInput(attrs={'class': 'form-control'}),
            'veloc_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, estudo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if estudo:
            self.fields['agrupamento'].queryset = ConfigAgrupamento.objects.filter(estudo=estudo)
            self.fields['param_vendas'].queryset = ParamVendas.objects.filter(estudo=estudo)


class ConstrucaoForm(forms.ModelForm):
    class Meta:
        model = Construcao
        exclude = ['estudo']
        widgets = {
            'curva': forms.Select(attrs={'class': 'form-select'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'constru_perc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'constru_inicio': forms.NumberInput(attrs={'class': 'form-control'}),
            'custo_m2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class ParamVendasForm(forms.ModelForm):
    class Meta:
        model = ParamVendas
        exclude = ['estudo']
        widgets = {f: forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
                   for f in [
                       'preco_venda', 'ato_perc', 'parc_perc', 'ref_perc',
                       'cha_perc', 'fin_parc_perc', 'fin_ref_perc',
                   ]}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['descricao', 'referencia']:
            self.fields[f].widget.attrs['class'] = 'form-control'
        for f in ['ato_qtde', 'parc_qtde', 'parc_apos', 'ref_qtde', 'ref_interv',
                  'cha_apos', 'fin_parc_qtde', 'fin_parc_apos', 'fin_ref_qtde',
                  'fin_ref_interv', 'tipo_financiamento']:
            self.fields[f].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned = super().clean()
        total = sum([
            cleaned.get('ato_perc', 0) or 0,
            cleaned.get('parc_perc', 0) or 0,
            cleaned.get('ref_perc', 0) or 0,
            cleaned.get('cha_perc', 0) or 0,
            cleaned.get('fin_parc_perc', 0) or 0,
            cleaned.get('fin_ref_perc', 0) or 0,
        ])
        if total and abs(float(total) - 100) > 0.01:
            raise forms.ValidationError(
                f'A soma dos percentuais deve ser 100%. Total atual: {total:.2f}%'
            )
        return cleaned


class CurvaForm(forms.ModelForm):
    class Meta:
        model = Curva
        fields = ['descricao']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CurvaMesForm(forms.ModelForm):
    class Meta:
        model = CurvaMes
        exclude = ['curva']
        widgets = {
            'curva_mes': forms.NumberInput(attrs={'class': 'form-control'}),
            'curva_perc': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
        }


class TipoForm(forms.ModelForm):
    class Meta:
        model = Tipo
        fields = ['descricao']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
        }
