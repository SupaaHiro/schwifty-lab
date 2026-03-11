import os

from dotenv import load_dotenv

from core.config import Config
from core.vectordb import build_embeddings, vbd_load_documents, vdb_builder

load_dotenv()


def test_initialize_kb() -> None:
    """Integration test: loads documents, builds the vector DB, and queries it."""

    cfg = Config.load_from_file("config.json")
    query = "What is LangChain?"

    docs_chunks = vbd_load_documents(str(cfg.vectordb.docs_path), cfg.vectordb.docs_glob)
    docs_total = len(docs_chunks)

    embeddings = build_embeddings(
        embedding_provider=cfg.vectordb.embedding_provider,
        embedding_name=cfg.vectordb.embedding_name,
    )

    builder = vdb_builder(
        embeddings=embeddings,
        path=str(cfg.vectordb.docs_path),
        glob=cfg.vectordb.docs_glob,
        db_path=str(cfg.vectordb.db_path),
        collection_name=cfg.vectordb.collection_name,
        recreate=False,
    )
    retriever = builder()

    print(f"Querying the vector database with '{query}'")
    docs = retriever.invoke(query)
    if not docs:
        raise ValueError("I found no relevant documentation in the internal KB (vector db).")

    docs_found = len(docs)
    print(f"Found {docs_found} documents:")
    for i, doc in enumerate(docs):
        source_path = doc.metadata.get("source", "Unknown")
        source = os.path.basename(source_path)
        print(f"Document {i + 1} {source}")

    assert docs_total == docs_found, f"Expected {docs_total} documents but found {docs_found}"
