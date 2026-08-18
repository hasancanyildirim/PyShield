import os
import glob
import chromadb
import ollama
from .document_loader import load_and_chunk_document

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
DEFAULT_DB_DIR = os.path.join(BASE_DIR, "chroma_db")


def get_embedding(text: str, model: str = "nomic-embed-text") -> list[float]:
    """
    Generates a dense vector embedding for a given text string using Ollama.
    """
    try:
        response = ollama.embeddings(model=model, prompt=text)
        return response["embedding"]
    except Exception:
        response = ollama.embed(model=model, input=text)
        return response["embeddings"][0]


def init_vector_store(
    persist_directory: str | None = None,
    collection_name: str = "novacloud_docs",
) -> chromadb.Collection:
    """
    Initializes a persistent ChromaDB client and gets or creates the target collection.
    """
    if persist_directory is None:
        persist_directory = DEFAULT_DB_DIR
    elif not os.path.isabs(persist_directory):
        persist_directory = os.path.join(BASE_DIR, persist_directory)

    client = chromadb.PersistentClient(path=persist_directory)
    collection = client.get_or_create_collection(
        name=collection_name, metadata={"hnsw:space": "cosine"}
    )
    return collection


def add_chunks_to_vector_store(
    collection: chromadb.Collection,
    chunks: list[dict],
    model: str = "nomic-embed-text",
) -> None:
    """
    Computes embeddings for chunks and saves ids, embeddings, text documents,
    and metadata dictionaries into ChromaDB.
    """
    if not chunks:
        return

    ids = [chunk["id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    embeddings = []
    for doc_text in documents:
        emb = get_embedding(doc_text, model=model)
        embeddings.append(emb)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def index_all_documents(
    kb_directory: str | None = None,
    persist_directory: str | None = None,
    collection_name: str = "novacloud_docs",
    chunk_size: int = 500,
    overlap: int = 100,
    model: str = "nomic-embed-text",
) -> chromadb.Collection:
    """
    Deterministically scans all Markdown documents in kb_directory,
    chunks them, and stores all chunks (both PUBLIC and INTERNAL) into ChromaDB.
    """
    if kb_directory is None:
        kb_directory = DEFAULT_KB_DIR
    elif not os.path.isabs(kb_directory):
        kb_directory = os.path.join(BASE_DIR, kb_directory)

    collection = init_vector_store(
        persist_directory=persist_directory, collection_name=collection_name
    )

    pattern = os.path.join(kb_directory, "*.md")
    md_files = sorted(glob.glob(pattern))

    all_chunks = []
    for file_path in md_files:
        doc_chunks = load_and_chunk_document(
            file_path, chunk_size=chunk_size, overlap=overlap
        )
        all_chunks.extend(doc_chunks)

    if all_chunks:
        add_chunks_to_vector_store(collection, all_chunks, model=model)

    return collection


def query_similar_chunks(
    collection: chromadb.Collection,
    query: str,
    top_k: int = 3,
    visibility_filter: str | None = None,
    model: str = "nomic-embed-text",
) -> list[dict]:
    """
    Generates an embedding for the query and retrieves top_k nearest chunks
    from ChromaDB. Optionally filters by visibility (e.g., visibility_filter="PUBLIC").
    """
    if collection.count() == 0:
        return []

    query_embedding = get_embedding(query, model=model)

    where_filter = None
    if visibility_filter:
        where_filter = {"visibility": visibility_filter}

    n_results = min(top_k, collection.count())

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    formatted_results = []
    if results and results.get("documents") and len(results["documents"]) > 0:
        docs = results["documents"][0]
        metas = (
            results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        )
        distances = (
            results["distances"][0] if results.get("distances") else [0.0] * len(docs)
        )
        ids = results["ids"][0] if results.get("ids") else [""] * len(docs)

        for i in range(len(docs)):
            formatted_results.append(
                {
                    "id": ids[i],
                    "text": docs[i],
                    "metadata": metas[i],
                    "distance": distances[i],
                }
            )

    return formatted_results
