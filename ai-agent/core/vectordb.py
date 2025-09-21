
from typing import Callable, TypedDict
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.embeddings.embeddings import Embeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings

import os


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


def vdb_build(embeddings: Embeddings | None, db_path: str, collection_name: str, docs_chunks: list[Document]) -> VectorStoreRetriever:
    """
    Initializes a Chroma vector database from a list of document chunks and returns a retriever for similarity search.
    Args:
      embeddings (Embeddings | None): The embedding model to use for vectorizing documents.
      db_path (str): Path to the directory where the vector database will be stored.
      collection_name (str): Name of the collection within the vector database.
      docs_chunks (list[Document]): List of document chunks to be added to the vector database.
    Returns:
      VectorStoreRetriever: A retriever object configured for similarity search over the vector database.
    Raises:
      Exception: If there is an error during the setup of the Chroma vector database.
    """

    if not os.path.exists(db_path):
        os.makedirs(db_path)

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


def get_vdb_builder(path: str, glob: str, embeddings: Embeddings | None, db_path: str, collection_name: str) -> Callable[[], VectorStoreRetriever]:
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
        docs_chunks = vbd_load_documents("../assets/docs", "**/*.md")
        print(f"Markdowns have been split into {len(docs_chunks)} chunks")

        model = "gpt-4o-mini"
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        # Note: The embedding model must be compatible with the LLM you are using.

        # Initialize the vector database (ChromaDB) and create a retriever
        return vdb_build(embeddings, r"../chroma_db", "internal_kb", docs_chunks)

    return _vectordb_builder
