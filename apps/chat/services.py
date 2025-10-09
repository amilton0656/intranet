from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile


class DocumentQAError(Exception):
    """Erro de dominio para operacoes de perguntas e respostas."""


@dataclass
class DocumentQAService:
    session_key: str | None = None

    def __post_init__(self) -> None:
        if not self.session_key:
            # Guarantee a filesystem-safe directory even when the session wasn't created yet.
            from uuid import uuid4

            self.session_key = uuid4().hex

        self.base_dir = Path(settings.MEDIA_ROOT)
        self.documents_dir = self.base_dir / 'uploads' / self.session_key
        self.chroma_dir = self.base_dir / 'chroma' / self.session_key

    def save_and_ingest(self, uploaded_file: UploadedFile) -> Path:
        try:
            self._reset_workspace()
            destination = self.documents_dir / uploaded_file.name
            self.documents_dir.mkdir(parents=True, exist_ok=True)

            with destination.open('wb') as target:
                for chunk in uploaded_file.chunks():
                    target.write(chunk)

            documents = self._load_documents(destination)
            if not documents:
                raise DocumentQAError('O documento enviado esta vazio.')

            self._build_vector_store(documents)
            return destination
        except DocumentQAError:
            raise
        except Exception as exc:
            raise DocumentQAError(
                f'Falha ao processar o documento: {exc}'
            ) from exc

    def ask(self, question: str, history: Sequence[dict[str, str]] | None = None) -> str:
        try:
            if not question:
                raise DocumentQAError('Informe uma pergunta.')

            if not self.chroma_dir.exists():
                raise DocumentQAError('Envie um documento antes de fazer perguntas.')

            vector_store = self._load_vector_store()
            history = history or []

            history_block = ''
            if history:
                formatted = [
                    f'Pergunta: {item.get("question", "")}\nResposta: {item.get("answer", "")}'
                    for item in history
                ]
                history_block = '\n\n'.join(formatted)

            try:
                from langchain.chains import RetrievalQA
                from langchain_openai import ChatOpenAI
            except ImportError as exc:
                raise DocumentQAError(
                    'LangChain ou OpenAI nao estao instalados corretamente. '
                    'Verifique as dependencias.'
                ) from exc

            prompt = question
            if history_block:
                prompt = (
                    'Contexto de conversa anterior:\n'
                    f'{history_block}\n\nNova pergunta: {question}'
                )

            try:
                llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
                chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    retriever=vector_store.as_retriever(search_kwargs={'k': 4}),
                    chain_type='stuff',
                    return_source_documents=False,
                )
                result = chain.invoke({'query': prompt})
            except Exception as exc:  # noqa: BLE001 - queremos converter em erro de dominio
                raise DocumentQAError(
                    'Nao foi possivel gerar a resposta. '
                    'Confirme se a chave OPENAI_API_KEY esta configurada e valida.'
                ) from exc

            return result.get('result', '').strip()
        except DocumentQAError:
            raise
        except Exception as exc:
            raise DocumentQAError(
                f'Falha ao gerar a resposta: {exc}'
            ) from exc

    def _build_vector_store(self, documents: Iterable) -> None:
        self.chroma_dir.mkdir(parents=True, exist_ok=True)

        try:
            from langchain_community.vectorstores import Chroma
            from langchain_openai import OpenAIEmbeddings
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError as exc:
            raise DocumentQAError(
                'Instale os pacotes langchain, langchain-community, langchain-openai e chromadb.'
            ) from exc

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = splitter.split_documents(list(documents))

        if not splits:
            raise DocumentQAError('Nao foi possivel dividir o documento em trechos utilizaveis.')

        try:
            embeddings = OpenAIEmbeddings()
            Chroma.from_documents(
                splits,
                embedding=embeddings,
                persist_directory=str(self.chroma_dir),
            )
        except Exception as exc:  # noqa: BLE001
            raise DocumentQAError(
                'Falha ao criar o indice vetorial. '
                'Verifique se o Chromadb esta instalado e se a chave OPENAI_API_KEY e valida.'
            ) from exc

    def _load_vector_store(self):
        try:
            from langchain_community.vectorstores import Chroma
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise DocumentQAError(
                'Instale os pacotes langchain, langchain-community, langchain-openai e chromadb.'
            ) from exc

        embeddings = OpenAIEmbeddings()
        return Chroma(
            persist_directory=str(self.chroma_dir),
            embedding_function=embeddings,
        )

    def _load_documents(self, file_path: Path):
        suffix = file_path.suffix.lower()

        try:
            if suffix == '.pdf':
                from langchain_community.document_loaders import PyPDFLoader

                loader = PyPDFLoader(str(file_path))
                return loader.load()

            if suffix in {'.txt', '.md'}:
                text = file_path.read_text(encoding='utf-8', errors='ignore')
                if not text.strip():
                    return []

                from langchain.schema import Document

                return [Document(page_content=text, metadata={'source': file_path.name})]
        except ImportError as exc:
            raise DocumentQAError(
                'Para processar este tipo de arquivo e necessario instalar dependencias adicionais (ex: pypdf).'
            ) from exc

        raise DocumentQAError('Formato de arquivo nao suportado. Use arquivos .txt ou .pdf.')

    def _reset_workspace(self) -> None:
        for directory in (self.documents_dir, self.chroma_dir):
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
