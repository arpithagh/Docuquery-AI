import chromadb
from sentence_transformers import SentenceTransformer
from pathlib import Path

EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")

CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
client = chromadb.PersistentClient(path=str(CHROMA_PATH))


def get_or_create_collection(collection_name: str = "documents"):
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )


def embed_and_store(chunks: list[dict], collection_name: str = "documents") -> int:
    collection = get_or_create_collection(collection_name)

    texts = [chunk["text"] for chunk in chunks]
    sources = [chunk["source"] for chunk in chunks]
    chunk_indices = [str(chunk["chunk_index"]) for chunk in chunks]

    embeddings = EMBEDDING_MODEL.encode(texts, show_progress_bar=False).tolist()

    ids = [f"{source}__chunk_{idx}" for source, idx in zip(sources, chunk_indices)]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=[{"source": s, "chunk_index": int(i)} for s, i in zip(sources, chunk_indices)]
    )

    return len(chunks)


def similarity_search(query: str, collection_name: str = "documents", top_k: int = 5) -> list[dict]:
    collection = get_or_create_collection(collection_name)

    if collection.count() == 0:
        return []

    query_embedding = EMBEDDING_MODEL.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"]
    )

    formatted = []
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        formatted.append({
            "text": doc,
            "source": meta["source"],
            "chunk_index": meta["chunk_index"],
            "similarity": round(1 - distance, 4)
        })

    return formatted


def multi_doc_similarity_search(query: str, collection_name: str = "documents", top_k: int = 5) -> list[dict]:
    """
    Retrieve chunks ensuring every uploaded document is represented,
    not just whichever scores highest globally.

    Strategy: fetch top-k chunks PER document, then merge and
    sort by similarity. This guarantees coverage across all docs
    while still prioritizing the most relevant chunks overall.
    """
    collection = get_or_create_collection(collection_name)

    if collection.count() == 0:
        return []

    docs = list_documents(collection_name)

    # Single document — no special handling needed, use normal search
    if len(docs) <= 1:
        return similarity_search(query, collection_name, top_k)

    query_embedding = EMBEDDING_MODEL.encode([query]).tolist()

    # Fetch a smaller per-document budget so the total stays close to top_k
    per_doc_k = max(1, top_k // len(docs))

    all_results = []
    seen_ids = set()

    for doc in docs:
        doc_name = doc["name"]
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(per_doc_k, doc["chunks"]),
            where={"source": doc_name},
            include=["documents", "metadatas", "distances"]
        )

        for chunk_text, meta, distance in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            chunk_id = f"{meta['source']}__{meta['chunk_index']}"
            if chunk_id not in seen_ids:
                seen_ids.add(chunk_id)
                all_results.append({
                    "text": chunk_text,
                    "source": meta["source"],
                    "chunk_index": meta["chunk_index"],
                    "similarity": round(1 - distance, 4)
                })

    # If under-filled (e.g. one doc had fewer chunks than its quota),
    # top up with the next-best global matches not already included
    if len(all_results) < top_k:
        remaining = top_k - len(all_results)
        global_results = similarity_search(query, collection_name, top_k=top_k * 2)
        for r in global_results:
            chunk_id = f"{r['source']}__{r['chunk_index']}"
            if chunk_id not in seen_ids and remaining > 0:
                seen_ids.add(chunk_id)
                all_results.append(r)
                remaining -= 1

    # Sort merged results by similarity, highest first
    all_results.sort(key=lambda x: x["similarity"], reverse=True)

    return all_results[:top_k]


def list_documents(collection_name: str = "documents") -> list[dict]:
    """Return documents with their chunk counts."""
    collection = get_or_create_collection(collection_name)
    if collection.count() == 0:
        return []

    results = collection.get(include=["metadatas"])

    # Count chunks per document
    counts = {}
    for meta in results["metadatas"]:
        src = meta["source"]
        counts[src] = counts.get(src, 0) + 1

    return [{"name": name, "chunks": count} for name, count in sorted(counts.items())]


def get_total_chunks(collection_name: str = "documents") -> int:
    collection = get_or_create_collection(collection_name)
    return collection.count()


def delete_document(filename: str, collection_name: str = "documents"):
    collection = get_or_create_collection(collection_name)
    results = collection.get(where={"source": filename})
    if results["ids"]:
        collection.delete(ids=results["ids"])