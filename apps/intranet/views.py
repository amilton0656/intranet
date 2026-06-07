import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Count, Min, Max
from django.shortcuts import render, redirect, get_object_or_404
from uteis import Uteis


def _fmt_blocos(nomes):
    if not nomes:       return '—'
    if len(nomes) == 1: return nomes[0]
    if len(nomes) == 2: return f"{nomes[0]} e {nomes[1]}"
    return ', '.join(nomes[:-1]) + f' e {nomes[-1]}'


def _get_bliss_info():
    try:
        from apps.incorporadora.models import Unidade, Bloco, Empreendimento
        from django.db.models import Sum

        def fmt(v):
            return f"{float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        def _grupo(t):
            if not t: return 'Outros'
            tl = t.lower()
            if '2d' in tl: return '2D'
            if '3d' in tl: return '3D'
            if 'loja' in tl: return 'Loja'
            return 'Outros'

        bliss = Empreendimento.objects.get(nome='BLISS LIVING')
        blocos = Bloco.objects.filter(empreendimento=bliss)
        qs = Unidade.objects.filter(bloco__in=blocos)

        areas = qs.aggregate(
            ap=Sum('area_privativa'),
            aa=Sum('area_privativa_acessoria'),
            ac=Sum('area_comum'),
        )
        ap = float(areas['ap'] or 0)
        aa = float(areas['aa'] or 0)
        ac = float(areas['ac'] or 0)

        grp_n = {}
        apts_qs = qs.filter(tipo='apartamento')
        for row in apts_qs.values('tipologia').annotate(n=Count('id')):
            g = _grupo(row['tipologia'])
            grp_n[g] = grp_n.get(g, 0) + row['n']

        apt_bloco_ids = set(apts_qs.values_list('bloco_id', flat=True))
        blocos_res = list(Bloco.objects.filter(id__in=apt_bloco_ids)
                          .exclude(nome__icontains='garagem')
                          .exclude(nome__icontains='hobby')
                          .order_by('ordem').values_list('nome', flat=True))

        return {
            'blocos':         _fmt_blocos(blocos_res),
            'd2_count':       grp_n.get('2D', 0),
            'd3_count':       grp_n.get('3D', 0),
            'loja_count':     qs.filter(tipo='loja').count(),
            'vagas_count':    qs.filter(tipo='garagem').count(),
            'hb_count':       qs.filter(tipo='hobby_box').count(),
            'area_priv':      f"{fmt(ap)} m²",
            'area_priv_acess':f"{fmt(aa)} m²",
            'area_comum':     f"{fmt(ac)} m²",
            'area_total':     f"{fmt(ap + aa + ac)} m²",
        }
    except Exception:
        return None


def _get_cota365_info():
    try:
        from apps.cota365.models import Unidade, Tabela
        from apps.incorporadora.models import Empreendimento as IncEmp, Unidade as IncUnidade
        from collections import defaultdict

        def fmt(v):
            return f"{v:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

        # Áreas: soma de todas as unidades (igual a _compute_areas do cota365)
        qs = Unidade.objects.all()
        area_priv       = sum(u.area_privativa       for u in qs)
        area_priv_acess = sum(u.area_priv_acessoria  for u in qs)
        area_comum      = sum(u.area_comum           for u in qs)
        area_total      = area_priv + area_priv_acess + area_comum

        # Contagem por grupo tipológico — filtra pela competência mais recente
        # (igual a _tabela_qs do dashboard; Tabela tem 1 linha por unidade×mês)
        from django.db.models import Max
        latest_comp = Tabela.objects.aggregate(latest=Max('competencia'))['latest']

        def _grupo(t):
            tl = t.lower()
            if 'studio' in tl: return 'Studio'
            if 'loja'   in tl: return 'Loja'
            return '2D'

        grp_n = defaultdict(int)
        for t in Tabela.objects.filter(competencia=latest_comp):
            if t.tipologia:
                grp_n[_grupo(t.tipologia)] += 1

        # Garagens e Hobby boxes (Unidade)
        tipo_counts = {t['tipo']: t['n'] for t in Unidade.objects.values('tipo').annotate(n=Count('id'))}

        # Blocos residenciais (incorporadora)
        from apps.incorporadora.models import Bloco as IncBloco
        emp_inc = IncEmp.objects.get(nome='COTA 365')
        apt_bloco_ids = set(IncUnidade.objects.filter(
            bloco__empreendimento=emp_inc, tipo='apartamento'
        ).values_list('bloco_id', flat=True))
        blocos_res = list(IncBloco.objects.filter(id__in=apt_bloco_ids)
                          .exclude(nome__icontains='garagem')
                          .exclude(nome__icontains='hobby')
                          .order_by('ordem').values_list('nome', flat=True))

        return {
            'blocos':        _fmt_blocos(blocos_res),
            'd2_count':      grp_n.get('2D', 0),
            'studio_count':  grp_n.get('Studio', 0),
            'loja_count':    grp_n.get('Loja', 0),
            'garagem_count': tipo_counts.get('Garagem', 0),
            'hb_count':      tipo_counts.get('Hobby box', 0),
            'area_priv':       f"{fmt(area_priv)} m²",
            'area_priv_acess': f"{fmt(area_priv_acess)} m²",
            'area_comum':      f"{fmt(area_comum)} m²",
            'area_total':      f"{fmt(area_total)} m²",
        }
    except Exception:
        return None

GRUPOS_DISPONIVEIS = [
    ('admin',        'Admin',        'Acesso total — todos os menus'),
    ('manager',      'Gerencial',    'Tabelas de Vendas e Gerencial'),
    ('financeiro',   'Financeiro',   'Menu Financeiro (Bliss / Cota 365)'),
    ('incorporadora','Incorporadora','App Incorporadora'),
]


@login_required
def intranet_home(request):
    uteis = Uteis()
    cubs = uteis.cubs_hoje()
    cubs_history = uteis.fetch_indices_last_12_months()

    context = {
        'cubs': cubs,
        'cubs_history': cubs_history,
        'cota365_info': _get_cota365_info(),
        'bliss_info':   _get_bliss_info(),
    }

    return render(request, 'intranet/intranet_home.html', context)


@login_required
def financeiro_home(request):
    if not request.user.groups.filter(name__in=['admin', 'financeiro']).exists():
        messages.error(request, 'Acesso restrito ao grupo Financeiro.')
        return redirect('intranet_home')
    return render(request, 'intranet/financeiro_home.html')


@login_required
def upload_pdfs(request):
    if not request.user.groups.filter(name='admin').exists():
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')

    downloads_dir = settings.MEDIA_ROOT / 'downloads'
    downloads_dir.mkdir(parents=True, exist_ok=True)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'upload':
            arquivo = request.FILES.get('arquivo')
            if not arquivo:
                messages.error(request, 'Nenhum arquivo selecionado.')
            elif not arquivo.name.lower().endswith('.pdf'):
                messages.error(request, 'Apenas arquivos PDF são permitidos.')
            else:
                destino = downloads_dir / arquivo.name
                with open(destino, 'wb') as f:
                    for chunk in arquivo.chunks():
                        f.write(chunk)
                messages.success(request, f'"{arquivo.name}" enviado com sucesso.')

        elif action == 'delete':
            nome = request.POST.get('nome', '')
            if nome and not ('/' in nome or '\\' in nome):
                alvo = downloads_dir / nome
                if alvo.exists():
                    alvo.unlink()
                    messages.success(request, f'"{nome}" excluído.')
                else:
                    messages.error(request, f'Arquivo "{nome}" não encontrado.')

        return redirect('intranet_uploads')

    pdfs = sorted(
        [
            {
                'nome': f.name,
                'tamanho': f'{f.stat().st_size / 1024:.1f} KB',
                'url': f'{settings.MEDIA_URL}downloads/{f.name}',
            }
            for f in downloads_dir.iterdir()
            if f.is_file() and f.suffix.lower() == '.pdf'
        ],
        key=lambda x: x['nome'],
    )

    return render(request, 'intranet/intranet_uploads.html', {'pdfs': pdfs})


def _apenas_admin(request):
    return request.user.is_authenticated and request.user.groups.filter(name='admin').exists()


@login_required
def usuario_list(request):
    if not _apenas_admin(request):
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')
    usuarios = User.objects.prefetch_related('groups').order_by('first_name', 'username')
    return render(request, 'intranet/usuario_list.html', {
        'usuarios': usuarios,
        'grupos_disponiveis': GRUPOS_DISPONIVEIS,
    })


@login_required
def usuario_edit(request, pk):
    if not _apenas_admin(request):
        messages.error(request, 'Acesso restrito ao grupo Admin.')
        return redirect('intranet_home')
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        novos_grupos = request.POST.getlist('grupos')
        grupos_obj = []
        for nome, _, _ in GRUPOS_DISPONIVEIS:
            grupo, _ = Group.objects.get_or_create(name=nome)
            if nome in novos_grupos:
                grupos_obj.append(grupo)
        usuario.groups.set(grupos_obj)
        messages.success(request, f'Grupos de "{usuario.get_full_name() or usuario.username}" atualizados.')
        return redirect('usuario_list')
    grupos_atuais = set(usuario.groups.values_list('name', flat=True))
    return render(request, 'intranet/usuario_form.html', {
        'usuario': usuario,
        'grupos_disponiveis': GRUPOS_DISPONIVEIS,
        'grupos_atuais': grupos_atuais,
    })
