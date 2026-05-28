"""
Monta o dicionário de contexto que é passado ao docxtpl para renderizar
minutas de contrato. Todas as variáveis disponíveis no template Word estão
documentadas aqui.
"""
from datetime import date as date_type
from dateutil.relativedelta import relativedelta

_MESES_PT = [
    'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]


def _data_extenso(d):
    return f'{d.day} de {_MESES_PT[d.month - 1]} de {d.year}'


def _brl(value):
    if value is None:
        return 'R$ 0,00'
    formatted = f'{float(value):_.2f}'
    return 'R$ ' + formatted.replace('.', ',').replace('_', '.')


def _endereco_str(p):
    partes = []
    if p.logradouro:
        partes.append(p.logradouro)
        if p.numero:
            partes[-1] += f', {p.numero}'
        if p.complemento:
            partes[-1] += f', {p.complemento}'
    if p.bairro:
        partes.append(p.bairro)
    if p.cidade:
        cidade = p.cidade
        if p.estado:
            cidade += f'/{p.estado}'
        partes.append(cidade)
    if p.cep:
        partes.append(f'CEP {p.cep}')
    return ' — '.join(partes)


def _qualificacao(p):
    """Monta o bloco de qualificação completo (PF ou PJ) para uso direto no contrato."""
    if p.tipo == 'juridica':
        partes = [p.nome.upper()]
        tipo_soc = p.tipo_societario or 'pessoa jurídica de direito privado'
        partes.append(tipo_soc)
        if p.cpf_cnpj:
            partes.append(f'inscrita no CNPJ sob nº {p.cpf_cnpj}')
        end = _endereco_str(p)
        if end:
            partes.append(f'com sede em {end}')
        if p.representante:
            partes.append(f'neste ato representada por {_qualificacao(p.representante)}')
        return ', '.join(partes)
    else:
        partes = [p.nome.upper()]
        if p.nacionalidade:
            partes.append(p.nacionalidade)
        if p.estado_civil:
            ec = p.get_estado_civil_display()
            if p.regime_bens:
                ec += f', pelo regime de {p.get_regime_bens_display()}'
            partes.append(ec)
        if p.profissao:
            partes.append(p.profissao)
        if p.rg_ie:
            rg = f'portador(a) do RG nº {p.rg_ie}'
            if p.rg_orgao_emissor:
                rg += f' {p.rg_orgao_emissor}'
            partes.append(rg)
        if p.cpf_cnpj:
            partes.append(f'inscrito(a) no CPF sob nº {p.cpf_cnpj}')
        end = _endereco_str(p)
        if end:
            partes.append(f'residente e domiciliado(a) em {end}')
        return ', '.join(partes)


def _pessoa_ctx(pessoa):
    if pessoa is None:
        return {}
    return {
        'nome':           pessoa.nome,
        'nome_upper':     pessoa.nome.upper(),
        'tipo':           pessoa.get_tipo_display(),
        'cpf_cnpj':       pessoa.cpf_cnpj,
        'rg':             pessoa.rg_ie,
        'rg_orgao':       pessoa.rg_orgao_emissor,
        'nacionalidade':  pessoa.nacionalidade,
        'profissao':      pessoa.profissao,
        'estado_civil':   pessoa.get_estado_civil_display() if pessoa.estado_civil else '',
        'regime_bens':    pessoa.get_regime_bens_display() if pessoa.regime_bens else '',
        'email':          pessoa.email,
        'telefone':       pessoa.telefone,
        'celular':        pessoa.celular,
        # Endereço
        'logradouro':     pessoa.logradouro,
        'num_endereco':   pessoa.numero,
        'complemento':    pessoa.complemento,
        'bairro':         pessoa.bairro,
        'cidade':         pessoa.cidade,
        'estado_uf':      pessoa.estado,
        'cep':            pessoa.cep,
        'endereco':       _endereco_str(pessoa),
        # Banco
        'banco':          pessoa.banco_nome,
        'banco_agencia':  pessoa.banco_agencia,
        'banco_conta':    pessoa.banco_conta,
        'banco_tipo':     pessoa.get_banco_tipo_conta_display() if pessoa.banco_tipo_conta else '',
        # PJ
        'tipo_societario': pessoa.tipo_societario,
        'representante':   _pessoa_ctx(pessoa.representante),
        # Qualificação completa — use direto no Word sem formatar na mão
        'qualificacao':   _qualificacao(pessoa),
    }


def _unidade_ctx(up):
    u = up.unidade
    return {
        'bloco':           u.bloco.nome,
        'numero':          u.numero,
        'tipo':            u.get_tipo_display(),
        'tipologia':       u.tipologia,
        'localizacao':     u.localizacao,
        'area_privativa':  str(u.area_privativa).replace('.', ','),
        'area_total':      str(u.area_total).replace('.', ','),
        'fracao_ideal':    str(u.fracao_ideal).replace('.', ','),
        'descricao1':      u.descricao1,
        'descricao2':      u.descricao2,
        'descricao3':      u.descricao3,
    }


def build_context(proposta):
    """
    Retorna o dicionário completo de variáveis para o docxtpl.

    Variáveis disponíveis no template Word (.docx):
    ─── Proposta ────────────────────────────────────────────────────────────
    {{ proposta_numero }}       ex: PROP-2026-0001
    {{ proposta_data }}         ex: 28/05/2026
    {{ proposta_data_extenso }} ex: 28 de maio de 2026
    {{ numero_contrato }}
    {{ observacoes }}

    ─── Empresa / Empreendimento ─────────────────────────────────────────────
    {{ empresa_nome }}
    {{ empresa_cnpj }}
    {{ empreendimento }}
    {{ tabela }}

    ─── Proponentes ─────────────────────────────────────────────────────────
    {{ proponente.nome }}           (primeiro proponente — atalho)
    {{ proponente.qualificacao }}   (bloco completo de qualificação)
    {{ proponente.cpf_cnpj }}
    {{ proponente.rg }}, {{ proponente.rg_orgao }}
    {{ proponente.nacionalidade }}, {{ proponente.profissao }}
    {{ proponente.estado_civil }},  {{ proponente.regime_bens }}
    {{ proponente.endereco }}
    {{ proponente.banco }}, {{ proponente.banco_agencia }}, {{ proponente.banco_conta }}
    {{ proponente.representante.nome }}  (se PJ)

    {{ proponente2.nome }}  (segundo proponente, para casais)

    {% for p in proponentes %}...{% endfor %}   (loop sobre todos)

    ─── Unidade ─────────────────────────────────────────────────────────────
    {{ unidade.bloco }}, {{ unidade.numero }}, {{ unidade.tipo }}
    {{ unidade.tipologia }}, {{ unidade.localizacao }}
    {{ unidade.area_privativa }}, {{ unidade.area_total }}, {{ unidade.fracao_ideal }}
    {% for u in unidades %}...{% endfor %}

    ─── Financeiro ───────────────────────────────────────────────────────────
    {{ valor_total }}              ex: R$ 500.000,00
    {% for s in series %}
      {{ s.label }}, {{ s.quantidade }}, {{ s.valor }}, {{ s.subtotal }}
      {{ s.primeiro_vencimento }}, {{ s.indexador }}
    {% endfor %}
    {% for p in parcelas %}
      {{ p.num }}, {{ p.serie }}, {{ p.vencimento }}, {{ p.valor }}
    {% endfor %}

    ─── Data de hoje ─────────────────────────────────────────────────────────
    {{ hoje }}           ex: 28/05/2026
    {{ hoje_extenso }}   ex: 28 de maio de 2026
    """
    participantes = list(
        proposta.participantes
        .select_related('pessoa', 'pessoa__representante')
        .all()
    )
    proponentes    = [_pessoa_ctx(pp.pessoa) for pp in participantes if pp.papel == 'proponente']
    intervenientes = [_pessoa_ctx(pp.pessoa) for pp in participantes if pp.papel == 'interveniente']
    coobrigados    = [_pessoa_ctx(pp.pessoa) for pp in participantes if pp.papel == 'coobrigado']

    unidades = [
        _unidade_ctx(up)
        for up in proposta.unidades.select_related('unidade__bloco__empreendimento').all()
    ]

    series_qs = list(proposta.series.filter(origem='proposta').order_by('ordem', 'primeiro_vencimento'))
    series = [
        {
            'label':              s.label,
            'quantidade':         s.quantidade,
            'valor':              _brl(s.valor),
            'subtotal':           _brl(s.subtotal),
            'primeiro_vencimento': s.primeiro_vencimento.strftime('%d/%m/%Y') if s.primeiro_vencimento else '',
            'indexador':          s.get_indexador_display(),
        }
        for s in series_qs
    ]

    # Fluxo cronológico completo
    parcelas_raw = []
    for s in series_qs:
        for i in range(s.quantidade):
            vcto = (s.primeiro_vencimento + relativedelta(months=i)
                    if s.primeiro_vencimento else None)
            parcelas_raw.append({
                'serie':    s.label,
                'parcela':  i + 1,
                'total':    s.quantidade,
                'vencimento': vcto,
                'valor':    s.valor,
            })
    parcelas_raw.sort(key=lambda x: (x['vencimento'] is None, x['vencimento'] or date_type.min))
    parcelas = [
        {
            'num':        n,
            'serie':      p['serie'],
            'parcela':    p['parcela'],
            'total':      p['total'],
            'vencimento': p['vencimento'].strftime('%d/%m/%Y') if p['vencimento'] else '',
            'valor':      _brl(p['valor']),
        }
        for n, p in enumerate(parcelas_raw, 1)
    ]

    hoje = date_type.today()

    return {
        # Proposta
        'proposta_numero':       proposta.numero,
        'proposta_data':         proposta.data.strftime('%d/%m/%Y'),
        'proposta_data_extenso': _data_extenso(proposta.data),
        'numero_contrato':       proposta.numero_contrato,
        'observacoes':           proposta.observacoes,

        # Empresa / Empreendimento
        'empresa_nome':   proposta.empreendimento.empresa.razao_social,
        'empresa_cnpj':   proposta.empreendimento.empresa.cnpj,
        'empreendimento': proposta.empreendimento.nome,
        'tabela':         proposta.tabela.nome,

        # Participantes
        'proponentes':     proponentes,
        'proponente':      proponentes[0] if proponentes else {},
        'proponente2':     proponentes[1] if len(proponentes) > 1 else {},
        'intervenientes':  intervenientes,
        'coobrigados':     coobrigados,

        # Unidades
        'unidades': unidades,
        'unidade':  unidades[0] if unidades else {},

        # Financeiro
        'series':      series,
        'parcelas':    parcelas,
        'valor_total': _brl(proposta.valor_proposto_total),

        # Data
        'hoje':         hoje.strftime('%d/%m/%Y'),
        'hoje_extenso': _data_extenso(hoje),
    }
