from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from core.config import Config
from core.vectordb import vbd_load_documents, vdb_build

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
    print("Loading and splitting markdown documents...")
    docs_chunks = vbd_load_documents(str(cfg.docs_path), str(cfg.docs_glob))
    imported_docs = len(docs_chunks)
    print(f"Markdowns have been split into {imported_docs} chunks")

    retriever = vdb_build(embedding_name=cfg.embedding_name,
                          db_path=str(cfg.db_path),
                          collection_name=str(cfg.collection_name),
                          docs_chunks=docs_chunks,
                          recreate=False)

    print(f"Querying the vector database with '{query}'")
    docs = retriever.invoke(query)
    if not docs:
        raise ValueError(
            "I found no relevant documentation in the internal KB (vector db).")

    found_docs = len(docs)
    print(f"Found {found_docs} documents:")
    for i, doc in enumerate(docs):
        source_path = doc.metadata.get("source", "No Unknown")
        source = os.path.basename(source_path)
        print(f"Document {i+1} {source}")

    # Assert
    assert imported_docs == found_docs, ValueError(
        f"Expected {imported_docs} documents but found {found_docs}")
