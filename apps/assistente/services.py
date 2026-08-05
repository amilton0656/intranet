from __future__ import annotations

import json
from datetime import date

import anthropic
from anthropic import beta_tool
from django.db.models import Count, Sum

from apps.bliss.models import Bliss
from apps.cota365.models import Parcela, Permuta, Unidade as UnidadeCota365, Venda
from apps.incorporadora.models import Unidade as UnidadeIncorporadora
from apps.pessoas.models import Pessoa

SYSTEM_PROMPT = (
    "Você é um assistente de pesquisa da intranet de uma incorporadora. Você tem acesso a "
    "ferramentas de busca sobre: vendas, parcelas, permutas e unidades (dados técnicos) do "
    "Cota 365, unidades do empreendimento Bliss Living, unidades de empreendimentos cadastrados na "
    "Incorporadora, cadastro de pessoas (clientes, corretores, imobiliárias, fornecedores) e "
    "resumo agregado de áreas do Cota 365. Use exclusivamente os dados retornados pelas "
    "ferramentas — nunca invente "
    "números, clientes, valores ou situações. Para perguntas sobre totais, somas ou contagens "
    "gerais, prefira uma ferramenta de resumo/agregação em vez de somar manualmente uma lista "
    "de resultados, pois listas têm limite de linhas e podem estar incompletas. Se a pergunta "
    "não puder ser respondida com os dados disponíveis, diga isso claramente em vez de supor. "
    "Responda sempre em português, formatado em Markdown, usando tabelas para listas de "
    "resultados."
)


@beta_tool
def buscar_vendas_cota365(
    cliente: str = "",
    unidade: str = "",
    situacao: str = "",
    imobiliaria: str = "",
    limite: int = 20,
) -> str:
    """Busca vendas registradas no Cota 365. Retorna uma lista de vendas em JSON.

    Args:
        cliente: Filtra por nome do cliente (busca parcial, sem diferenciar maiúsculas/minúsculas).
        unidade: Filtra por número da unidade (busca parcial).
        situacao: Filtra por situação da venda (ex: "Vendido", "Distrato").
        imobiliaria: Filtra por nome da imobiliária.
        limite: Número máximo de resultados (padrão 20, máximo 100).
    """
    qs = Venda.objects.all()
    if cliente:
        qs = qs.filter(cliente__icontains=cliente)
    if unidade:
        qs = qs.filter(unidade__icontains=unidade)
    if situacao:
        qs = qs.filter(situacao__icontains=situacao)
    if imobiliaria:
        qs = qs.filter(imobiliaria__icontains=imobiliaria)
    qs = qs.order_by('-data_venda')[:max(1, min(limite, 100))]
    resultado = [
        {
            'numero': v.numero,
            'cliente': v.cliente,
            'unidade': v.unidade,
            'situacao': v.situacao,
            'valor_contrato': v.valor_contrato,
            'data_venda': v.data_venda.isoformat() if v.data_venda else None,
            'imobiliaria': v.imobiliaria,
        }
        for v in qs
    ]
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def buscar_unidades_cota365(
    unidade: str = "",
    tipo: str = "",
    limite: int = 20,
) -> str:
    """Busca unidades cadastradas no Cota 365 (dados técnicos: tipo, áreas, fração ideal).
    Não inclui cliente, valor ou status de venda — para isso use buscar_vendas_cota365.
    Retorna uma lista em JSON.

    Args:
        unidade: Filtra por número da unidade (busca parcial).
        tipo: Filtra por tipo da unidade (busca parcial, ex: "apartamento", "garagem").
        limite: Número máximo de resultados (padrão 20, máximo 100).
    """
    qs = UnidadeCota365.objects.all()
    if unidade:
        qs = qs.filter(unidade__icontains=unidade)
    if tipo:
        qs = qs.filter(tipo__icontains=tipo)
    qs = qs.order_by('unidade')[:max(1, min(limite, 100))]
    resultado = [
        {
            'unidade': u.unidade,
            'tipo': u.tipo,
            'complemento_tipo': u.complemento_tipo,
            'area_privativa': u.area_privativa,
            'area_priv_acessoria': u.area_priv_acessoria,
            'area_comum': u.area_comum,
            'area_total': u.area_privativa + u.area_priv_acessoria + u.area_comum,
            'fracao_ideal': u.fracao_ideal,
        }
        for u in qs
    ]
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def buscar_permutas_cota365(unidade: str = "", limite: int = 50) -> str:
    """Lista unidades do Cota 365 marcadas como permuta (unidade dada em compensação ao
    proprietário original do terreno, sem venda em dinheiro). O total retornado é exato
    (contado direto no banco), mesmo que a lista de unidades venha limitada. Retorna JSON.

    Args:
        unidade: Filtra por número da unidade (busca parcial). Vazio lista todas.
        limite: Número máximo de unidades detalhadas na lista (padrão 50, máximo 100).
    """
    qs = Permuta.objects.all()
    if unidade:
        qs = qs.filter(unidade__icontains=unidade)
    total = qs.count()
    unidades = list(qs.order_by('unidade').values_list('unidade', flat=True)[:max(1, min(limite, 100))])
    resultado = {
        'total_unidades_permuta': total,
        'unidades': unidades,
    }
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def buscar_unidades_bliss(
    unidade: str = "",
    bloco: str = "",
    situacao: str = "",
    cliente: str = "",
    limite: int = 20,
) -> str:
    """Busca unidades do empreendimento Bliss Living. Retorna uma lista de unidades em JSON.

    Args:
        unidade: Filtra por número da unidade (busca parcial).
        bloco: Filtra por bloco (busca parcial).
        situacao: Filtra por situação (ex: "Disponível", "Vendida").
        cliente: Filtra por nome do cliente comprador (busca parcial).
        limite: Número máximo de resultados (padrão 20, máximo 100).
    """
    qs = Bliss.objects.all()
    if unidade:
        qs = qs.filter(unidade__icontains=unidade)
    if bloco:
        qs = qs.filter(bloco__icontains=bloco)
    if situacao:
        qs = qs.filter(situacao__icontains=situacao)
    if cliente:
        qs = qs.filter(cliente__icontains=cliente)
    qs = qs.order_by('bloco', 'unidade')[:max(1, min(limite, 100))]
    resultado = [
        {
            'bloco': u.bloco,
            'unidade': u.unidade,
            'situacao': u.situacao,
            'tipologia': u.tipologia,
            'area_privativa': float(u.area_privativa),
            'valor_tabela': float(u.valor_tabela),
            'valor_venda': float(u.valor_venda),
            'cliente': u.cliente,
            'data_venda': u.data_venda.isoformat() if u.data_venda else None,
        }
        for u in qs
    ]
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def buscar_parcelas_cota365(
    cliente: str = "",
    unidade: str = "",
    situacao: str = "",
    limite: int = 30,
) -> str:
    """Busca parcelas (contas a receber) do Cota 365. Retorna uma lista em JSON.

    Args:
        cliente: Filtra por nome do cliente (busca parcial).
        unidade: Filtra por número da unidade (busca parcial).
        situacao: "pago" (tem data_pagamento), "vencido" (vencimento passou e não foi pago)
            ou "pendente" (ainda não venceu e não foi pago). Vazio retorna todas.
        limite: Número máximo de resultados (padrão 30, máximo 100).
    """
    qs = Parcela.objects.all()
    if cliente:
        qs = qs.filter(cliente__icontains=cliente)
    if unidade:
        qs = qs.filter(unidade__icontains=unidade)
    hoje = date.today()
    if situacao == 'pago':
        qs = qs.filter(data_pagamento__isnull=False)
    elif situacao == 'vencido':
        qs = qs.filter(data_pagamento__isnull=True, vencimento__lt=hoje)
    elif situacao == 'pendente':
        qs = qs.filter(data_pagamento__isnull=True, vencimento__gte=hoje)
    qs = qs.order_by('vencimento')[:max(1, min(limite, 100))]
    resultado = []
    for p in qs:
        if p.data_pagamento:
            situacao_calc = 'pago'
        elif p.vencimento and p.vencimento < hoje:
            situacao_calc = 'vencido'
        else:
            situacao_calc = 'pendente'
        resultado.append({
            'titulo': p.titulo,
            'parcela': p.parcela,
            'unidade': p.unidade,
            'cliente': p.cliente,
            'vencimento': p.vencimento.isoformat() if p.vencimento else None,
            'data_pagamento': p.data_pagamento.isoformat() if p.data_pagamento else None,
            'valor': p.valor,
            'valor_original': p.valor_original,
            'situacao': situacao_calc,
        })
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def buscar_unidades_incorporadora(
    empreendimento: str = "",
    bloco: str = "",
    numero: str = "",
    status: str = "",
    tipo: str = "",
    limite: int = 30,
) -> str:
    """Busca unidades de empreendimentos cadastrados no app Incorporadora. Retorna JSON.

    Args:
        empreendimento: Filtra por nome do empreendimento (busca parcial).
        bloco: Filtra por nome do bloco (busca parcial).
        numero: Filtra por número da unidade (busca parcial).
        status: "disponivel", "reservado", "vendido", "permuta", "bloqueado" ou "qa".
        tipo: "apartamento", "garagem", "hobby_box", "sala" ou "loja".
        limite: Número máximo de resultados (padrão 30, máximo 100).
    """
    qs = UnidadeIncorporadora.objects.select_related('bloco', 'bloco__empreendimento')
    if empreendimento:
        qs = qs.filter(bloco__empreendimento__nome__icontains=empreendimento)
    if bloco:
        qs = qs.filter(bloco__nome__icontains=bloco)
    if numero:
        qs = qs.filter(numero__icontains=numero)
    if status:
        qs = qs.filter(status=status)
    if tipo:
        qs = qs.filter(tipo=tipo)
    qs = qs.order_by('bloco__empreendimento__nome', 'bloco__nome', 'numero')[:max(1, min(limite, 100))]
    resultado = [
        {
            'empreendimento': u.bloco.empreendimento.nome,
            'bloco': u.bloco.nome,
            'numero': u.numero,
            'tipo': u.get_tipo_display(),
            'tipologia': u.tipologia,
            'status': u.get_status_display(),
            'area_total': float(u.area_total),
            'valor_tabela': float(u.valor_tabela),
            'cliente': u.cliente_nome,
        }
        for u in qs
    ]
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def buscar_pessoas(
    nome: str = "",
    papel: str = "",
    cidade: str = "",
    limite: int = 20,
) -> str:
    """Busca pessoas cadastradas (clientes, corretores, imobiliárias, fornecedores). Retorna JSON.

    Não retorna CPF/CNPJ, RG, endereço completo nem dados bancários — apenas identificação e
    contato básico, por política de privacidade.

    Args:
        nome: Filtra por nome/razão social (busca parcial).
        papel: "cliente", "corretor", "imobiliaria" ou "fornecedor".
        cidade: Filtra por cidade (busca parcial).
        limite: Número máximo de resultados (padrão 20, máximo 100).
    """
    qs = Pessoa.objects.filter(ativo=True)
    if nome:
        qs = qs.filter(nome__icontains=nome)
    if papel == 'cliente':
        qs = qs.filter(is_cliente=True)
    elif papel == 'corretor':
        qs = qs.filter(is_corretor=True)
    elif papel == 'imobiliaria':
        qs = qs.filter(is_imobiliaria=True)
    elif papel == 'fornecedor':
        qs = qs.filter(is_fornecedor=True)
    if cidade:
        qs = qs.filter(cidade__icontains=cidade)
    qs = qs.order_by('nome')[:max(1, min(limite, 100))]
    resultado = [
        {
            'nome': p.nome,
            'tipo': p.get_tipo_display(),
            'papeis': p.papeis_display,
            'cidade': p.cidade,
            'estado': p.estado,
            'telefone': p.telefone or p.celular,
            'email': p.email,
        }
        for p in qs
    ]
    return json.dumps(resultado, ensure_ascii=False)


@beta_tool
def resumo_areas_cota365(tipo: str = "") -> str:
    """Retorna o resumo agregado de áreas das unidades cadastradas no Cota 365.

    A soma é feita diretamente no banco de dados (não a partir de uma lista limitada),
    então o total é sempre exato, mesmo havendo muitas unidades. Use esta ferramenta para
    perguntas sobre área total, área privativa total etc. — não para listar unidades
    individualmente.

    Args:
        tipo: Filtra por tipo de unidade (busca parcial, ex: "apartamento", "garagem").
            Vazio soma todas as unidades cadastradas.
    """
    qs = UnidadeCota365.objects.all()
    if tipo:
        qs = qs.filter(tipo__icontains=tipo)
    agregados = qs.aggregate(
        total_unidades=Count('id'),
        area_privativa_total=Sum('area_privativa'),
        area_priv_acessoria_total=Sum('area_priv_acessoria'),
        area_comum_total=Sum('area_comum'),
    )
    area_privativa_total = agregados['area_privativa_total'] or 0
    area_priv_acessoria_total = agregados['area_priv_acessoria_total'] or 0
    area_comum_total = agregados['area_comum_total'] or 0
    resultado = {
        'total_unidades': agregados['total_unidades'] or 0,
        'area_privativa_total_m2': round(area_privativa_total, 2),
        'area_priv_acessoria_total_m2': round(area_priv_acessoria_total, 2),
        'area_comum_total_m2': round(area_comum_total, 2),
        'area_total_m2': round(area_privativa_total + area_priv_acessoria_total + area_comum_total, 2),
    }
    return json.dumps(resultado, ensure_ascii=False)


TOOLS = [
    buscar_vendas_cota365,
    buscar_unidades_cota365,
    buscar_permutas_cota365,
    buscar_unidades_bliss,
    buscar_parcelas_cota365,
    buscar_unidades_incorporadora,
    buscar_pessoas,
    resumo_areas_cota365,
]


MODELOS_DISPONIVEIS = {
    'claude-sonnet-5': 'Sonnet 5 (mais preciso)',
    'claude-haiku-4-5': 'Haiku 4.5 (mais barato)',
}
MODELO_PADRAO = 'claude-haiku-4-5'


class AssistenteError(Exception):
    """Erro de domínio ao consultar o assistente de pesquisa."""


def perguntar(pergunta: str, modelo: str = MODELO_PADRAO) -> str:
    pergunta = (pergunta or '').strip()
    if not pergunta:
        raise AssistenteError('Informe uma pergunta.')
    if modelo not in MODELOS_DISPONIVEIS:
        modelo = MODELO_PADRAO

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=modelo,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=TOOLS,
        messages=[{'role': 'user', 'content': pergunta}],
    )

    final_message = None
    for message in runner:
        final_message = message

    if final_message is None:
        raise AssistenteError('Não foi possível obter uma resposta.')

    texto = next((b.text for b in final_message.content if b.type == 'text'), '')
    if not texto:
        raise AssistenteError('A resposta veio vazia.')
    return texto
