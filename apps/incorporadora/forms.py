from django import forms
from .models import Empresa, Empreendimento, Bloco, Unidade, TabelaVendas, SeriePagamento


class EmpresaForm(forms.ModelForm):
    class Meta:
        model = Empresa
        fields = ['razao_social', 'cnpj', 'ativo']
        widgets = {
            'razao_social': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razão Social',
                'autofocus': True,
            }),
            'cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'XX.XXX.XXX/XXXX-XX',
                'maxlength': '18',
                'id': 'id_cnpj',
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EmpreendimentoForm(forms.ModelForm):
    class Meta:
        model = Empreendimento
        fields = ['empresa', 'nome', 'status']
        widgets = {
            'empresa': forms.Select(attrs={'class': 'form-select'}),
            'nome':    forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'status':  forms.Select(attrs={'class': 'form-select'}),
        }


class BlocoForm(forms.ModelForm):
    class Meta:
        model = Bloco
        fields = ['empreendimento', 'nome', 'ordem']
        widgets = {
            'empreendimento': forms.Select(attrs={'class': 'form-select'}),
            'nome':           forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'ordem':          forms.NumberInput(attrs={'class': 'form-control text-end'}),
        }


_dec = {'class': 'form-control text-end'}

class UnidadeForm(forms.ModelForm):
    class Meta:
        model = Unidade
        fields = [
            'bloco', 'ordem', 'pagina', 'numero', 'numeros_adicionais', 'tipo', 'tipologia', 'localizacao',
            'area_privativa', 'area_privativa_acessoria', 'area_comum',
            'fracao_ideal', 'valor_tabela', 'status',
            'unidade_principal',
            'descricao1', 'descricao2', 'descricao3',
        ]
        widgets = {
            'bloco':                    forms.Select(attrs={'class': 'form-select'}),
            'ordem':                    forms.NumberInput(attrs={'class': 'form-control text-end'}),
            'pagina':                   forms.NumberInput(attrs={'class': 'form-control text-end'}),
            'numero':                   forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'numeros_adicionais':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: M03, HB60'}),
            'tipo':                     forms.Select(attrs={'class': 'form-select', 'id': 'id_tipo'}),
            'tipologia':                forms.TextInput(attrs={'class': 'form-control'}),
            'localizacao':              forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Térreo, Subsolo, Mezanino...'}),
            'area_privativa':           forms.NumberInput(attrs=_dec),
            'area_privativa_acessoria': forms.NumberInput(attrs=_dec),
            'area_comum':               forms.NumberInput(attrs=_dec),
            'fracao_ideal':             forms.NumberInput(attrs={**_dec, 'step': '0.000001'}),
            'valor_tabela':             forms.NumberInput(attrs=_dec),
            'status':                   forms.Select(attrs={'class': 'form-select'}),
            'unidade_principal':        forms.Select(attrs={'class': 'form-select'}),
            'descricao1':               forms.TextInput(attrs={'class': 'form-control'}),
            'descricao2':               forms.TextInput(attrs={'class': 'form-control'}),
            'descricao3':               forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, bloco=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bloco:
            self.fields['unidade_principal'].queryset = Unidade.objects.filter(
                bloco=bloco,
                tipo__in=['apartamento', 'sala', 'loja'],
            ).order_by('ordem', 'numero')
        else:
            self.fields['unidade_principal'].queryset = Unidade.objects.none()
        self.fields['unidade_principal'].empty_label = '— Nenhuma —'


class TabelaVendasForm(forms.ModelForm):
    class Meta:
        model = TabelaVendas
        fields = ['nome', 'modalidade', 'cub_referencia', 'data_referencia', 'data_inicio', 'data_fim', 'ativa']
        widgets = {
            'nome':            forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'modalidade':      forms.Select(attrs={'class': 'form-select'}),
            'cub_referencia':  forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.01'}),
            'data_referencia': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_inicio':     forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'data_fim':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'ativa':           forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class SeriePagamentoForm(forms.ModelForm):
    class Meta:
        model = SeriePagamento
        fields = ['tipo', 'periodicidade', 'primeiro_vencimento', 'quantidade', 'percentual', 'indice', 'ordem']
        widgets = {
            'tipo':                forms.Select(attrs={'class': 'form-select'}),
            'periodicidade':       forms.Select(attrs={'class': 'form-select'}),
            'primeiro_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'quantidade':          forms.NumberInput(attrs={'class': 'form-control text-end'}),
            'percentual':          forms.NumberInput(attrs={'class': 'form-control text-end', 'step': '0.001', 'placeholder': 'Ex: 20.000'}),
            'indice':              forms.Select(attrs={'class': 'form-select'}),
            'ordem':               forms.NumberInput(attrs={'class': 'form-control text-end'}),
        }

    def __init__(self, *args, tabela=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._tabela = tabela

    def clean_percentual(self):
        from decimal import Decimal
        percentual = self.cleaned_data.get('percentual')
        if percentual is None or self._tabela is None:
            return percentual
        outras = (
            SeriePagamento.objects
            .filter(tabela=self._tabela)
            .exclude(pk=self.instance.pk if self.instance.pk else None)
        )
        soma = sum(s.percentual for s in outras if s.percentual) or Decimal('0')
        disponivel = Decimal('100') - soma
        if percentual > disponivel:
            raise forms.ValidationError(
                f'Percentual inválido. Já alocado: {soma}%. '
                f'Disponível: {disponivel:.3f}%.'
            )
        return percentual
