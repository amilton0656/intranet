from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa


def render_to_pdf(template_src, context, filename='relatorio.pdf'):
    template = get_template(template_src)
    html = template.render(context)
    buffer = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode('utf-8')), buffer)
    if pdf.err:
        return HttpResponse('Erro ao gerar PDF', status=500)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
