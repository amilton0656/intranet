import io
import os
import tempfile

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from docxtpl import DocxTemplate

from apps.propostas.models import Proposta
from .models import MinutaContrato, ContratoGerado
from .forms import MinutaContratoForm
from .context import build_context


# ── CRUD de Minutas ───────────────────────────────────────────────────────────

@login_required
def minuta_list(request):
    minutas = MinutaContrato.objects.all()
    return render(request, 'contratos/minuta_list.html', {'minutas': minutas})


@login_required
def minuta_create(request):
    form = MinutaContratoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Minuta cadastrada com sucesso.')
        return redirect('contratos:minuta_list')
    return render(request, 'contratos/minuta_form.html', {'form': form, 'titulo': 'Nova Minuta'})


@login_required
def minuta_edit(request, pk):
    minuta = get_object_or_404(MinutaContrato, pk=pk)
    form = MinutaContratoForm(request.POST or None, request.FILES or None, instance=minuta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Minuta atualizada com sucesso.')
        return redirect('contratos:minuta_list')
    return render(request, 'contratos/minuta_form.html', {
        'form': form, 'titulo': 'Editar Minuta', 'obj': minuta,
    })


@login_required
def minuta_delete(request, pk):
    minuta = get_object_or_404(MinutaContrato, pk=pk)
    if request.method == 'POST':
        minuta.delete()
        messages.success(request, 'Minuta excluída.')
        return redirect('contratos:minuta_list')
    return render(request, 'contratos/minuta_confirm_delete.html', {'obj': minuta})


# ── Referência de Variáveis ───────────────────────────────────────────────────

VARIAVEIS = [
    {
        'categoria': 'Proposta',
        'icone': 'bi-file-earmark-text',
        'itens': [
            ('{{ proposta_numero }}',       'Número da proposta',              'PROP-2026-0001'),
            ('{{ proposta_data }}',         'Data da proposta',                '28/05/2026'),
            ('{{ proposta_data_extenso }}', 'Data da proposta por extenso',    '28 de maio de 2026'),
            ('{{ numero_contrato }}',       'Número do contrato',              'CT-2026-001'),
            ('{{ observacoes }}',           'Observações da proposta',         ''),
        ],
    },
    {
        'categoria': 'Empresa / Empreendimento',
        'icone': 'bi-buildings',
        'itens': [
            ('{{ empresa_nome }}',   'Razão social da incorporadora',  'NEWWAY INCORPORAÇÕES LTDA'),
            ('{{ empresa_cnpj }}',   'CNPJ da incorporadora',          '00.000.000/0001-00'),
            ('{{ empreendimento }}', 'Nome do empreendimento',         'RESIDENCIAL HORIZONTE'),
            ('{{ tabela }}',         'Nome da tabela de vendas',       'Tabela Jun/2026'),
        ],
    },
    {
        'categoria': 'Proponente',
        'icone': 'bi-person',
        'itens': [
            ('{{ proponente.qualificacao }}',   'Bloco completo de qualificação (PF ou PJ)', ''),
            ('{{ proponente.nome }}',           'Nome completo',             'JOÃO DA SILVA'),
            ('{{ proponente.nome_upper }}',     'Nome em maiúsculas',        'JOÃO DA SILVA'),
            ('{{ proponente.cpf_cnpj }}',       'CPF ou CNPJ',              '000.000.000-00'),
            ('{{ proponente.rg }}',             'RG',                        '1.234.567'),
            ('{{ proponente.rg_orgao }}',       'Órgão emissor do RG',       'SSP/SP'),
            ('{{ proponente.nacionalidade }}',  'Nacionalidade',             'brasileiro(a)'),
            ('{{ proponente.profissao }}',      'Profissão',                 'engenheiro(a)'),
            ('{{ proponente.estado_civil }}',   'Estado civil',              'Casado(a)'),
            ('{{ proponente.regime_bens }}',    'Regime de bens',            'Comunhão Parcial de Bens'),
            ('{{ proponente.email }}',          'E-mail',                    'joao@email.com'),
            ('{{ proponente.telefone }}',       'Telefone',                  '(48) 3333-3333'),
            ('{{ proponente.celular }}',        'Celular',                   '(48) 99999-9999'),
            ('{{ proponente.endereco }}',       'Endereço completo formatado', 'Rua X, 100 — Centro — Florianópolis/SC — CEP 88000-000'),
            ('{{ proponente.banco }}',          'Nome do banco',             'Banco do Brasil'),
            ('{{ proponente.banco_agencia }}',  'Agência bancária',          '1234-5'),
            ('{{ proponente.banco_conta }}',    'Conta bancária',            '12345-6'),
            ('{{ proponente.tipo_societario }}','Tipo societário (PJ)',       'Ltda'),
            ('{{ proponente.representante.nome }}',        'Nome do representante legal (PJ)', ''),
            ('{{ proponente.representante.qualificacao }}','Qualificação do representante (PJ)', ''),
        ],
    },
    {
        'categoria': 'Segundo Proponente (casal)',
        'icone': 'bi-people',
        'itens': [
            ('{{ proponente2.nome }}',          'Nome do segundo proponente', 'MARIA DA SILVA'),
            ('{{ proponente2.qualificacao }}',  'Qualificação completa',      ''),
            ('{{ proponente2.cpf_cnpj }}',      'CPF',                        '000.000.000-00'),
            ('{{ proponente2.profissao }}',     'Profissão',                  ''),
            ('{{ proponente2.estado_civil }}',  'Estado civil',               ''),
            ('{{ proponente2.regime_bens }}',   'Regime de bens',             ''),
        ],
    },
    {
        'categoria': 'Loop — Todos os proponentes',
        'icone': 'bi-arrow-repeat',
        'itens': [
            ('{% for p in proponentes %}...{% endfor %}', 'Itera sobre todos os proponentes', ''),
            ('{{ p.nome }}',         'Dentro do loop: nome',         ''),
            ('{{ p.qualificacao }}', 'Dentro do loop: qualificação', ''),
        ],
    },
    {
        'categoria': 'Unidade',
        'icone': 'bi-door-open',
        'itens': [
            ('{{ unidade.bloco }}',          'Nome do bloco',          'Bloco A'),
            ('{{ unidade.numero }}',         'Número da unidade',      '101'),
            ('{{ unidade.tipo }}',           'Tipo da unidade',        'Apartamento'),
            ('{{ unidade.tipologia }}',      'Tipologia',              '2 Dorm'),
            ('{{ unidade.localizacao }}',    'Localização',            '1º andar'),
            ('{{ unidade.area_privativa }}', 'Área privativa (m²)',    '62,50'),
            ('{{ unidade.area_total }}',     'Área total (m²)',        '72,00'),
            ('{{ unidade.fracao_ideal }}',   'Fração ideal',           '0,001234'),
            ('{{ unidade.descricao1 }}',     'Descrição adicional 1',  ''),
            ('{{ unidade.descricao2 }}',     'Descrição adicional 2',  ''),
        ],
    },
    {
        'categoria': 'Financeiro',
        'icone': 'bi-currency-dollar',
        'itens': [
            ('{{ valor_total }}', 'Valor total da proposta', 'R$ 500.000,00'),
        ],
    },
    {
        'categoria': 'Loop — Séries de pagamento',
        'icone': 'bi-arrow-repeat',
        'itens': [
            ('{% for s in series %}...{% endfor %}',  'Itera sobre as séries',        ''),
            ('{{ s.label }}',              'Nome da série',              'Sinal'),
            ('{{ s.quantidade }}',         'Número de parcelas',         '12'),
            ('{{ s.valor }}',              'Valor da parcela',           'R$ 1.000,00'),
            ('{{ s.subtotal }}',           'Subtotal da série',          'R$ 12.000,00'),
            ('{{ s.primeiro_vencimento }}','Primeiro vencimento',        '01/07/2026'),
            ('{{ s.indexador }}',          'Indexador',                  'INCC'),
        ],
    },
    {
        'categoria': 'Loop — Fluxo cronológico',
        'icone': 'bi-arrow-repeat',
        'itens': [
            ('{% for p in parcelas %}...{% endfor %}', 'Itera sobre todas as parcelas em ordem', ''),
            ('{{ p.num }}',       'Número sequencial',  '1'),
            ('{{ p.serie }}',     'Nome da série',      'Intermediárias'),
            ('{{ p.parcela }}',   'Nº dentro da série', '3'),
            ('{{ p.total }}',     'Total da série',     '24'),
            ('{{ p.vencimento }}','Data de vencimento', '01/09/2026'),
            ('{{ p.valor }}',     'Valor da parcela',   'R$ 2.500,00'),
        ],
    },
    {
        'categoria': 'Data',
        'icone': 'bi-calendar3',
        'itens': [
            ('{{ hoje }}',         'Data de hoje',              '28/05/2026'),
            ('{{ hoje_extenso }}', 'Data de hoje por extenso',  '28 de maio de 2026'),
        ],
    },
]


@login_required
def variaveis(request):
    return render(request, 'contratos/variaveis.html', {'grupos': VARIAVEIS})


# ── Geração de Contrato ───────────────────────────────────────────────────────

def _gerar_docx_buffer(minuta, ctx):
    """Renderiza o template Word e devolve um BytesIO com o .docx."""
    tpl = DocxTemplate(minuta.arquivo.path)
    tpl.render(ctx)
    buf = io.BytesIO()
    tpl.save(buf)
    buf.seek(0)
    return buf


def _converter_para_pdf(docx_buffer):
    """Converte um BytesIO de .docx para bytes de PDF.

    Windows: usa docx2pdf (Microsoft Word via COM).
    Linux:   usa LibreOffice headless.
    """
    import sys, subprocess

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_docx:
        tmp_docx.write(docx_buffer.read())
        tmp_docx_path = tmp_docx.name

    tmp_pdf_path = tmp_docx_path.replace('.docx', '.pdf')
    try:
        if sys.platform == 'win32':
            from docx2pdf import convert
            convert(tmp_docx_path, tmp_pdf_path)
        else:
            result = subprocess.run(
                [
                    'libreoffice', '--headless', '--convert-to', 'pdf',
                    '--outdir', os.path.dirname(tmp_docx_path),
                    tmp_docx_path,
                ],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f'LibreOffice: {result.stderr.strip()}')
            if not os.path.exists(tmp_pdf_path):
                raise RuntimeError('LibreOffice não gerou o PDF.')

        with open(tmp_pdf_path, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(tmp_docx_path):
            os.unlink(tmp_docx_path)
        if os.path.exists(tmp_pdf_path):
            os.unlink(tmp_pdf_path)


@login_required
def contrato_gerar(request, numero):
    proposta = get_object_or_404(Proposta, numero=numero)
    minutas  = MinutaContrato.objects.filter(ativo=True)

    if request.method == 'POST':
        minuta_pk = request.POST.get('minuta', '').strip()
        formato   = request.POST.get('formato', 'pdf')

        if not minuta_pk:
            messages.error(request, 'Selecione uma minuta antes de gerar o contrato.')
            return redirect('contratos:contrato_gerar', numero=numero)

        minuta = get_object_or_404(MinutaContrato, pk=minuta_pk, ativo=True)

        ctx          = build_context(proposta)
        docx_buffer  = _gerar_docx_buffer(minuta, ctx)
        timestamp    = timezone.now().strftime('%Y%m%d_%H%M%S')

        if formato == 'docx':
            nome = f'contrato_{proposta.numero}_{timestamp}.docx'
            response = HttpResponse(
                docx_buffer.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            )
            response['Content-Disposition'] = f'attachment; filename="{nome}"'
            return response

        # PDF — converte, salva e devolve como download
        try:
            pdf_bytes = _converter_para_pdf(docx_buffer)
        except Exception as e:
            messages.error(request, f'Erro ao converter para PDF: {e}')
            return redirect('contratos:contrato_gerar', numero=numero)

        nome = f'contrato_{proposta.numero}_{timestamp}.pdf'
        contrato = ContratoGerado(
            proposta=proposta,
            minuta=minuta,
            gerado_por=request.user,
        )
        contrato.arquivo.save(nome, ContentFile(pdf_bytes), save=True)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nome}"'
        return response

    return render(request, 'contratos/contrato_gerar.html', {
        'proposta': proposta,
        'minutas':  minutas,
    })


@login_required
def contrato_excluir(request, pk):
    contrato = get_object_or_404(ContratoGerado, pk=pk)
    numero   = contrato.proposta.numero
    if request.method == 'POST':
        contrato.delete()
        messages.success(request, 'Contrato excluído.')
    return redirect('propostas:proposta_detail', numero=numero)
