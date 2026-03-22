"""
PDF ve metin dosyalarından ChromaDB bilgi bankası oluşturma ve sorgulama.

- Ücretli (varsayılan): OpenAI embedding → chroma_db/
- Ücretsiz (QUAKEGUARD_FREE=true): yerel HuggingFace embedding → chroma_db_local/
  (OpenAI kotası gerekmez; ilk çalıştırmada model indirilebilir.)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
COLLECTION_NAME = "quakeguard_protocols"
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

_DEFAULT_HF_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _chroma_dir() -> Path:
    return BASE_DIR / ("chroma_db_local" if config.is_free_mode() else "chroma_db")


def _get_embeddings():
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if config.is_free_mode():
        from langchain_community.embeddings import HuggingFaceEmbeddings

        model = os.getenv("HF_EMBEDDING_MODEL", _DEFAULT_HF_MODEL).strip() or _DEFAULT_HF_MODEL
        return HuggingFaceEmbeddings(model_name=model)

    from langchain_openai import OpenAIEmbeddings

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY tanımlı değil. Ücretsiz mod için .env içine QUAKEGUARD_FREE=true ve GROQ_API_KEY ekleyin."
        )
    return OpenAIEmbeddings(model="text-embedding-3-small")


def _list_pdf_paths() -> list[Path]:
    if not DATA_DIR.is_dir():
        return []
    return sorted(DATA_DIR.glob("*.pdf"))


def _list_txt_paths() -> list[Path]:
    if not DATA_DIR.is_dir():
        return []
    return sorted(DATA_DIR.glob("*.txt"))


def _load_documents():
    docs = []
    for pdf in _list_pdf_paths():
        loader = PyPDFLoader(str(pdf))
        docs.extend(loader.load())
    for txt in _list_txt_paths():
        loader = TextLoader(str(txt), encoding="utf-8")
        docs.extend(loader.load())
    return docs


def build_or_load_vectorstore() -> Chroma:
    chroma_dir = _chroma_dir()
    embeddings = _get_embeddings()

    if chroma_dir.exists() and any(chroma_dir.iterdir()):
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(chroma_dir),
        )

    chroma_dir.mkdir(parents=True, exist_ok=True)
    docs = _load_documents()
    if not docs:
        raise FileNotFoundError(
            f"Bilgi bankası için {DATA_DIR} altında en az bir .pdf veya .txt bulunamadı."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    splits = splitter.split_documents(docs)

    return Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(chroma_dir),
    )


def search_safety_protocols(query: str, k: int = 4) -> str:
    vs = build_or_load_vectorstore()
    results = vs.similarity_search(query, k=k)
    parts = []
    for i, doc in enumerate(results, start=1):
        text = (doc.page_content or "").strip()
        if text:
            parts.append(f"[Parça {i}]\n{text}")
    return "\n\n".join(parts) if parts else "İlgili protokol pasajı bulunamadı."


def reset_knowledge_base() -> None:
    """Geliştirme / yeniden indeks için chroma klasörünü temizler."""
    import shutil

    d = _chroma_dir()
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
