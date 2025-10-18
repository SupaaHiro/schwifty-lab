from dotenv import load_dotenv
from core.config import Config
from core.vectordb import vbd_load_documents, vdb_builder

import os

# Load environment variables from .env file
# Set OPENAI_API_KEY in your .env file for authentication
# See https://platform.openai.com/account/api-keys
load_dotenv()


def test_initialize_kb() -> None:
    """
    Test function to initialize and query a Chroma vector database with documents from a specified folder.
    """

    # Prepare
    # Load configuration
    cfg = Config.load_from_file("config.json")
    query = "What is LangChain?"

    # Act
    docs_chunks = vbd_load_documents(str(cfg.docs_path), str(cfg.docs_glob))
    docs_total = len(docs_chunks)

    builder = vdb_builder(path=str(cfg.docs_path),
                          glob=cfg.docs_glob,
                          embedding_name=cfg.embedding_name,
                          db_path=str(cfg.db_path),
                          collection_name=cfg.collection_name,
                          recreate=False)
    retriever = builder()

    print(f"Querying the vector database with '{query}'")
    docs = retriever.invoke(query)
    if not docs:
        raise ValueError(
            "I found no relevant documentation in the internal KB (vector db).")

    docs_found = len(docs)
    print(f"Found {docs_found} documents:")
    for i, doc in enumerate(docs):
        source_path = doc.metadata.get("source", "No Unknown")
        source = os.path.basename(source_path)
        print(f"Document {i+1} {source}")

    # Assert
    assert docs_total == docs_found, ValueError(
        f"Expected {docs_total} documents but found {docs_found}")
