
from typing import Callable
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings

import chromadb
import os


def vbd_load_documents(path: str, glob: str, chunk_size=1000, chunk_overlap=200) -> list[Document]:
    """
    Loads and splits documents from a specified folder using a glob pattern.
    Args:
      path (str): Path to the folder containing documents.
      glob (str): Glob pattern to match document files.
    Returns:
      list[Document]: A list of document chunks after splitting.
    Raises:
      FileNotFoundError: If the specified folder does not exist.
      Exception: If an error occurs during document loading.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"Markdown folder not found: {path}")

    md_loader = DirectoryLoader(
        path,
        glob=glob,
        loader_cls=TextLoader,
        show_progress=False
    )
    try:
        md_docs = md_loader.load()
    except Exception as e:
        print(f"Error loading documents for {path}: {e}")
        raise

    # Split documents into chunks
    docs_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs_chunks = docs_splitter.split_documents(md_docs)

    return docs_chunks


def vdb_builder(path: str, glob: str, embedding_name: str, db_path: str, collection_name: str, recreate: bool) -> Callable[[], VectorStoreRetriever]:
    """
    Creates a builder function that initializes or updates a ChromaDB vector store collection with embedded document chunks, and returns a retriever for similarity search.
    Args:
      embedding_name (str): Name of the embedding model to use for converting documents into vector representations.
      db_path (str): Path to the persistent ChromaDB database.
      collection_name (str): Name of the collection to create or update in ChromaDB.
      docs_chunks (list[Document]): List of document chunks to be embedded and stored.
      recreate (bool): If True, resets the database before building the collection.
    Returns:
      Callable[[], VectorStoreRetriever]: A function that returns a VectorStoreRetriever for querying the collection.
    Raises:
      Exception: If there are issues initializing the database or upserting documents.
    """

    def _builder_function() -> VectorStoreRetriever:
        # Load and split documents
        docs_chunks = vbd_load_documents(path, glob)

        # Initialize embedding model
        embeddings = OpenAIEmbeddings(model=embedding_name)
        # Note: It must be compatible with the LLM you are using.

        # Initialize ChromaDB client
        client = chromadb.PersistentClient(
            path=db_path)
        if recreate or not os.path.exists(db_path):
            client.reset()
            print(f"Initialized ChromaDB at {db_path}")

        # Update collection with documents
        collection = client.get_or_create_collection(
            name=collection_name, embedding_function=None)
        for doc in docs_chunks:
            doc_content = doc.page_content if hasattr(
                doc, "page_content") else str(doc)
            doc_id = doc.metadata.get('source', '')
            if not doc_id:
                doc_id = f"Unknown Source [{str(hash(doc_content))}]"
            collection.upsert(
                ids=[doc_id],
                documents=[doc_content],
                embeddings=[embeddings.embed_query(doc_content)],
                metadatas=[doc.metadata]
            )
        print(
            f"ChromaDB collection '{collection_name}' updated with {len(docs_chunks)} documents.")

        # Get the retriever
        retriever = VectorStoreRetriever(
            vectorstore=Chroma(
                collection_name=collection_name,
                embedding_function=embeddings,
                client=client
            ),
            search_type="similarity",
            # K is the amount of chunks to return (usually between 3 and 5 is good)
            search_kwargs={"k": 5}
        )

        return retriever

    return _builder_function
