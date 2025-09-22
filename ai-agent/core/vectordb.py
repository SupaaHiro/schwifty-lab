
from typing import Callable
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.embeddings.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever
from core.utils import deprecated

import chromadb
import shutil
import os


@deprecated("Use vdb_build instead")
def vdb_build_old(embeddings: Embeddings, db_path: str, collection_name: str, docs_chunks: list[Document], recreate: bool) -> VectorStoreRetriever:
    """
    Initializes a Chroma vector database from a list of document chunks and returns a retriever for similarity search.
    Args:
      embeddings (Embeddings | None): The embedding model to use for vectorizing documents.
      db_path (str): Path to the directory where the vector database will be stored.
      collection_name (str): Name of the collection within the vector database.
      docs_chunks (list[Document]): List of document chunks to be added to the vector database.
      recreate: Whether to recreate the database if it already exists.
    Returns:
      VectorStoreRetriever: A retriever object configured for similarity search over the vector database.
    Raises:
      Exception: If there is an error during the setup of the Chroma vector database.
    """

    # Clear existing database directory if it exists
    if recreate and os.path.exists(db_path):
        shutil.rmtree(db_path)
    os.makedirs(db_path, exist_ok=True)

    try:
        vectorstore = Chroma.from_documents(
            documents=docs_chunks,
            embedding=embeddings,
            persist_directory=db_path,
            collection_name=collection_name
        )
        print(f"Created ChromaDB vector store!")

    except Exception as e:
        print(f"Error setting up ChromaDB: {str(e)}")
        raise

    # Now we create our retriever
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        # K is the amount of chunks to return (usually between 3 and 5 is good)
        search_kwargs={"k": 5}
    )

    return retriever


def vbd_load_documents(path: str, glob: str) -> list[Document]:
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
        show_progress=True
    )
    try:
        md_docs = md_loader.load()
        print(f"Loaded {len(md_docs)} documents")
    except Exception as e:
        print(f"Error loading Markdown: {e}")
        raise

    # Split documents into chunks
    docs_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )

    docs_chunks = docs_splitter.split_documents(md_docs)

    return docs_chunks


def vdb_build(embeddings: Embeddings, db_path: str, collection_name: str, docs_chunks: list[Document], recreate: bool) -> VectorStoreRetriever:
    """
    Builds or updates a ChromaDB vector store collection with embedded document chunks and returns a retriever for similarity search.
    Args:
      embeddings (Embeddings): Embedding model/function to convert documents into vector representations.
      db_path (str): Path to the persistent ChromaDB database.
      collection_name (str): Name of the collection to create or update in ChromaDB.
      docs_chunks (list[Document]): List of document chunks to be embedded and stored.
      recreate (bool): If True, resets the database before building the collection.
    Returns:
      VectorStoreRetriever: A retriever object for performing similarity searches on the vector store.
    Raises:
      Exception: If there are issues initializing the database or upserting documents.
    """

    # Initialize ChromaDB client
    client = chromadb.PersistentClient(path=db_path)
    if recreate or not os.path.exists(db_path):
        client.reset()
        print(f"Initialized ChromaDB at {db_path}")

    # Update collection with documents
    collection = client.get_or_create_collection(name=collection_name)
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


def get_vdb_builder(path: str, glob: str, embeddings: Embeddings, db_path: str, collection_name: str) -> Callable[[], VectorStoreRetriever]:
    """
    Returns a function that loads documents from a specified folder, splits them into chunks and builds a Chroma vector database retriever.
    """

    def _vectordb_builder() -> VectorStoreRetriever:
        """
                Loads documents from a specified folder, splits them into chunks, and builds a Chroma vector database retriever.
                Args:
                  path (str): Path to the folder containing documents.
                  glob (str): Glob pattern to match document files.
                  embeddings (Embeddings | None): The embedding model to use for vectorizing documents.
                  db_path (str): Path to the directory where the vector database will be stored.
                  collection_name (str): Name of the collection within the vector database.
                Returns:
                  VectorStoreRetriever: A retriever object configured for similarity search over the vector database.
                Raises:
                  FileNotFoundError: If the specified folder does not exist.
                  Exception: If an error occurs during document loading or vector database setup.
            """

        # Load documents from a folder containing Markdown files
        docs_chunks = vbd_load_documents(path, glob)
        print(f"Markdowns have been split into {len(docs_chunks)} chunks")

        # Initialize the vector database (ChromaDB) and create a retriever
        return vdb_build(embeddings, db_path, collection_name, docs_chunks, recreate=False)

    return _vectordb_builder
