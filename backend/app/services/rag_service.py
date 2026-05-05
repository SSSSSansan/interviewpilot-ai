# backend/app/services/rag_service.py

import os
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import TokenTextSplitter

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"))

CHROMA_HOST = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8001))

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small"
)

client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
collection = client.get_or_create_collection(
    name="interview_knowledge",
    embedding_function=openai_ef
)


def ingest_documents(folder_path: str):
    """Читает все .txt файлы из папки, чанкует, эмбеддит, кладёт в ChromaDB."""
    splitter = TokenTextSplitter(chunk_size=512, chunk_overlap=50)

    docs, ids, metadatas = [], [], []

    for filename in os.listdir(folder_path):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(folder_path, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{filename}_{i}"
            docs.append(chunk)
            ids.append(chunk_id)
            metadatas.append({"source": filename, "chunk_index": i})

    if not docs:
        print("Нет документов для ingestion.")
        return

    collection.add(documents=docs, ids=ids, metadatas=metadatas)
    print(f"✅ Ingested {len(docs)} chunks из {folder_path}")


def retrieve_context(query: str, role: str, top_k: int = 3) -> str:
    """
    Ищет top_k релевантных чанков по запросу.
    Возвращает строку с чанками разделёнными разделителем.
    """
    results = collection.query(
        query_texts=[f"{role}: {query}"],
        n_results=top_k
    )

    chunks = results["documents"][0]
    if not chunks:
        return ""

    return "\n\n---\n\n".join(chunks)