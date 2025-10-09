from __future__ import annotations

import logging

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .forms import BlissMemorialForm, ChatForm
from .services import DocumentQAError, DocumentQAService

logger = logging.getLogger(__name__)


@require_http_methods(['GET', 'POST'])
def chat_view(request):
    history = request.session.get('chat_history', [])
    active_document = request.session.get('active_document_name')
    answer = None

    if request.method == 'POST':
        form = ChatForm(request.POST, request.FILES)
        if not request.session.session_key:
            request.session.create()

        service = DocumentQAService(session_key=request.session.session_key)

        if form.is_valid():
            document = form.cleaned_data.get('document')
            question = form.cleaned_data.get('question')

            try:
                if document:
                    service.save_and_ingest(document)
                    active_document = document.name
                    request.session['active_document_name'] = active_document
                    history = []

                if question:
                    answer = service.ask(question, history=history)
                    history.append({'question': question, 'answer': answer})

                request.session['chat_history'] = history
                request.session.modified = True

            except DocumentQAError as exc:
                form.add_error(None, str(exc))
            except Exception:
                logger.exception('Erro inesperado ao processar o chat.')
                form.add_error(
                    None,
                    'Ocorreu um erro inesperado ao processar sua solicitação. '
                    'Tente novamente mais tarde ou contate o suporte.',
                )

        # When the form is invalid, errors will be displayed by the template.
    else:
        form = ChatForm()

    context = {
        'form': form,
        'history': history,
        'answer': answer,
        'active_document': active_document,
    }
    return render(request, 'chat/chat.html', context)


@require_http_methods(['GET', 'POST'])
def bliss_memorial_view(request):
    history = request.session.get('bliss_history', [])
    answer = None

    if request.method == 'POST':
        form = BlissMemorialForm(request.POST)
        if form.is_valid():
            question = form.cleaned_data.get('question')
            if question:
                try:
                    if not request.session.session_key:
                        request.session.create()

                    service = DocumentQAService(session_key=request.session.session_key)
                    answer = service.ask(question, history=history)
                    history.append({'question': question, 'answer': answer})
                    request.session['bliss_history'] = history
                    request.session.modified = True

                except DocumentQAError as exc:
                    form.add_error(None, str(exc))
                except Exception:
                    logger.exception('Erro inesperado ao processar o memorial Bliss.')
                    form.add_error(
                        None,
                        'Ocorreu um erro inesperado ao processar sua solicitação. '
                        'Tente novamente mais tarde ou contate o suporte.',
                    )
            else:
                form.add_error('question', 'Informe uma pergunta.')
    else:
        form = BlissMemorialForm()

    return render(
        request,
        'chat/bliss_memorial.html',
        {'form': form, 'answer': answer},
    )
