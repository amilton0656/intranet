from django.conf import settings
from django.urls import reverse

_MEDIA = settings.MEDIA_URL

COTA365_TABELAS = [
    {"name": "Cota 365 - Tabela Curta (Todas Tipologias) - bancária",
        "url": f"{_MEDIA}downloads/COTA 365 - Curta Todas - bancária.pdf"},
    {"name": "Cota 365 - Tabela Longa (2 Dorm) - bancária",
        "url": f"{_MEDIA}downloads/COTA 365 - Longa StudioLojas - bancária.pdf"},
    {"name": "Cota 365 - Tabela Longa (Studio e Lojas) - bancária",
        "url": f"{_MEDIA}downloads/COTA 365 - Longa 2Dorm - bancária.pdf"},
]

EMPREENDEDIMENTO_LINKS = [
    {"name": "Bliss Living - bancária",
        "url": f"{_MEDIA}downloads/BLISS LIVING - bancaria.pdf"},
    *COTA365_TABELAS,
    {"name": "Green Village Residence - bancária",
        "url": f"{_MEDIA}downloads/GREEN VILLAGE RESIDENCE - bancária.pdf"},
    {"name": "Imóveis de Terceiros - Bombinhas",
        "url": f"{_MEDIA}downloads/IMOVEIS DE TERCEIROS - BOMBINHAS - bancária.pdf"},
    {"name": "Imóveis de Terceiros - Grande Florianópolis",
        "url": f"{_MEDIA}downloads/IMÓVEIS DE TERCEIROS - GRANDE FLORIANÓPOLIS - bancária.pdf"},
    {"name": "Max & Flora - Locação",
        "url": f"{_MEDIA}downloads/MAX & FLORA - locação.pdf"},
    {"name": "Punta Blu Mall Boutique - bancária",
        "url": f"{_MEDIA}downloads/PUNTA BLU MALL BOUTIQUE - bancária.pdf"},
    {"name": "Punta Blu Mall Boutique - direta",
        "url": f"{_MEDIA}downloads/PUNTA BLU MALL BOUTIQUE - direta.pdf"},
    {"name": "Punta Blu Mall Boutique - locação",
        "url": f"{_MEDIA}downloads/PUNTA BLU MALL BOUTIQUE - locação.pdf"},
    {"name": "Punta Blu Residence - bancária",
        "url": f"{_MEDIA}downloads/PUNTA BLU RESIDENCE - bancária.pdf"},
]

ADMINISTRATIVO_LINKS = [
    {"name": "Organograma", "url": "#"},
    {"name": "Manual de Funções", "url": "#"},
    {"name": "Normas Internas", "url": "#"},
]

NEWS_LINKS = [
    {"name": "Globo", "url": "https://www.globo.com"},
    {"name": "Jornal O Globo", "url": "https://oglobo.globo.com"},
    {"name": "Folha de São Paulo", "url": "https://www.folha.uol.com.br"},
    {"name": "Estadão", "url": "https://www.estadao.com.br"},
    {"name": "Valor Econômico", "url": "https://valor.globo.com"},
    {"name": "Época Negócios", "url": "https://epocanegocios.globo.com"},
    {"name": "InfoMoney", "url": "https://www.infomoney.com.br"},
    {"name": "MoneyTimes", "url": "https://www.moneytimes.com.br"},
    {"name": "CNN Brasil", "url": "https://www.cnnbrasil.com.br"},
    {"name": "BBC Brasil", "url": "https://www.bbc.com/portuguese"},
    {"name": "Jovem Pan", "url": "https://jovempan.com.br"},
    {"name": "Revista Veja", "url": "https://veja.abril.com.br"},
    {"name": "Revista Época", "url": "https://oglobo.globo.com/epoca"},
    {"name": "Revista Isto é", "url": "https://istoe.com.br"},
    {"name": "NSC Total", "url": "https://www.nsctotal.com.br/dc"},
    {"name": "Notícias do Dia", "url": "https://ndmais.com.br"},
    {"name": "Revista Exame", "url": "https://exame.com"},
    {"name": "Terra", "url": "https://www.terra.com.br"},
    {"name": "UOL", "url": "https://www.uol.com.br"},
]

NEWS_LINKS_SECONDARY = [
    {"name": "Jovem Pan", "url": "https://jovempan.com.br"},
    {"name": "Revista Veja", "url": "https://veja.abril.com.br"},
    {"name": "Revista Época", "url": "https://oglobo.globo.com/epoca"},
    {"name": "Revista Isto e", "url": "https://istoe.com.br"},
    {"name": "NSC Total", "url": "https://www.nsctotal.com.br/dc"},
    {"name": "Notícias do Dia", "url": "https://ndmais.com.br"},
    {"name": "Revista Exame", "url": "https://exame.com"},
    {"name": "Terra", "url": "https://www.terra.com.br"},
    {"name": "UOL", "url": "https://www.uol.com.br"},
]

BANK_LINKS = [
    {"name": "Banco do Brasil", "url": "https://www.bb.com.br"},
    {"name": "Brasil - Office", "url": 'file:///C:/BancoBrasil/officeIE/index.html'},
    {"name": "Bradesco", "url": "https://www.bradesco.com.br"},
    {"name": "Caixa Econômica Federal", "url": "https://www.caixa.gov.br"},
    {"name": "Credicard", "url": "https://www.credicard.com.br"},
    {"name": "Fibra", "url": 'https://portal.bancofibra.com.br/produtos.html'},
    {"name": "Inter", "url": "https://www.bancointer.com.br"},
    {"name": "Itau Empresas", "url": "https://www.itau.com.br/empresas"},
    {"name": "Real", "url": "https://www.secureweb.com.br"},
    {"name": "Redasset", "url": "https://redasset.com.br"},
    {"name": "Safra", "url": "https://www.safra.com.br/pessoa-juridica.htm"},
    {"name": "Santander", "url": "https://www.santander.com.br"},
    {"name": "Sicoob", "url": "https://www.sicoob.com.br/sicoobnet/"},
    {"name": "Sicredi", "url": "https://www.sicredi.com.br"},
    {"name": "Unicred", "url": "https://www.unicred.com.br/valorcapital/home"},
    {"name": "Unilos", "url": "https://www.unilos.coop.br"},
]

PUBLIC_AGENCY_LINKS = [
    {"name": "Presidência - Planalto", "url": "http://www.jfsc.gov.br"},
    {"name": "Tribunal de Justiça Federal - SC", "url": "http://www.tj.sc.gov.br"},
    {"name": "Receita Federal", "url": "https://www.gov.br/receitafederal/pt-br"},
    {"name": "Previdência Social", "url": "http://www.previdenciasocial.gov.br"},
    {"name": "Fazenda Estadual", "url": "http://www.sef.sc.gov.br"},
    {"name": "Junta Comercial de SC", "url": "http://www.jucesc.sc.gov.br"},
    {"name": "Prefeitura Mun. Florianópolis", "url": "http://www.pmf.sc.gov.br"},
    {"name": "Fazenda Municipal", "url": "http://sefinnet.pmf.sc.gov.br"},
    {"name": "Sinduscon - Fpolis", "url": "http://www.sinduscon-fpolis.org.br"},
    {"name": "Serasa", "url": "http://www.connectsa.com.br"},
]

USEFUL_LINKS = [
    {"name": "Simulador de Financiamento",
        "url": "http://www.financiamento.com.br/simulador/"},
    {"name": "CEP", "url": "http://www.buscacep.correios.com.br"},
    {"name": "COTA", "url": "https://www.cota.com.br"},
    {"name": "CREA", "url": "http://www.crea-sc.org.br"},
    {"name": "DANFE", "url": "https://www.danfeonline.com.br/"},
    {"name": "Google", "url": "http://www.google.com.br"},
    {"name": "Horário Oficial do Brasil", "url": "http://www.horariodebrasilia.org"},
    {"name": "Código do Banco", "url": "https://www.codigobanco.com"},
    {"name": "Sienge", "url": "https://cotaemp.sienge.com.br/"},
    {"name": "CV", "url": "https://cota.cvcrm.com.br/"},
    {"name": "Fastbuilt", "url": "https://app.fastbuilt.com.br/dashboard/"},
    {"name": "Prevision", "url": "https://app.prevision.com.br/login"},
    {"name": "Hinc", "url": "https://www.hinc.com.br/"},
    {"name": "Hinc-beta", "url": "https://beta.hinc.com.br/"},
    {"name": "WhatsApp", "url": "https://web.whatsapp.com/"},
    {"name": "Gemini", "url": "https://gemini.google.com/app"},
    {"name": "ChatGPT", "url": "https://chat.openai.com/auth/login"},
]

GERENCIAL_LINKS = [
    {"name": "Bliss - Resumo", "url": reverse('bliss_resumo_pdf')},
    {"name": "Cota365 - Resumo", "url": reverse('cota365:export_dashboard')},
    {"name": "Cota365 - Fluxo Mensal", "url": reverse('cota365:export_fluxo') + '?format=pdf'},
]

ADMIN_LINKS = [
    {"name": "Índices", "url": reverse('indices:indice_list')},
    {"name": "Tabela Bliss", "url": "/bliss/"},
    {"name": "Chat - IA", "url": reverse('chat:chat')},
    {"name": "Cota365", "url": reverse('cota365:index')},
    {"name": "Tabelas PDF", "url": reverse('intranet_uploads')},
]

# reverse("indice_list")


def navbar_links(request):
    user = getattr(request, 'user', None)
    show_gerencial_menu = False
    show_admin_menu = False

    show_financeiro_menu = False

    show_incorporadora_menu = False

    if user and user.is_authenticated:
        group_names = set(user.groups.values_list("name", flat=True))
        show_gerencial_menu = bool(group_names & {"admin", "manager"})
        show_admin_menu = "admin" in group_names
        show_financeiro_menu = bool(group_names & {"admin", "financeiro"})
        show_incorporadora_menu = bool(group_names & {"admin", "incorporadora"})

    return {
        "empreendimento_links": EMPREENDEDIMENTO_LINKS,
        "administrativo_links": ADMINISTRATIVO_LINKS,
        "news_links": NEWS_LINKS,
        "news_links_secondary": NEWS_LINKS_SECONDARY,
        "bank_links": BANK_LINKS,
        "public_agency_links": PUBLIC_AGENCY_LINKS,
        "useful_links": USEFUL_LINKS,
        "gerencial_links": GERENCIAL_LINKS if show_gerencial_menu else [],
        "admin_links": ADMIN_LINKS if show_admin_menu else [],
        "show_gerencial_menu": show_gerencial_menu,
        "show_admin_menu": show_admin_menu,
        "show_financeiro_menu": show_financeiro_menu,
        "show_incorporadora_menu": show_incorporadora_menu,
    }
