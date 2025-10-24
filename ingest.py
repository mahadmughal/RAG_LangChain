"""Document ingestion pipeline for RAG system using LangChain and Chroma."""
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

DATA_DIR = Path("dataset/refined")
PERSIST_DIR = os.getenv("CHROMA_DIR", ".chroma_rag")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def load_markdown_docs():
    """
    Loads all .md files under dataset/refined/ using UnstructuredMarkdownLoader
    (keeps code blocks reasonably intact).
    """
    loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        show_progress=True,
        use_multithreading=True
    )
    docs = loader.load()
    # Set a source path in metadata for later citation
    for d in docs:
        if "source" not in d.metadata:
            d.metadata["source"] = d.metadata.get(
                "filename") or d.metadata.get("source") or "unknown.md"
    return docs


def chunk_docs(docs):
    """
    Chunk with markdown-friendly separators; large enough for code snippets
    but small enough for precise retrieval.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n```", "\n# ", "\n## ",
                    "\n### ", "\n- ", "\n", " ", "", "\n• "],
        length_function=len,
        add_start_index=True,
    )
    return splitter.split_documents(docs)


def main():
    """Main function to ingest documents and build the vector store."""
    if not DATA_DIR.exists():
        raise SystemExit(f"Missing {DATA_DIR}/ — add your .md files there.")

    print("📥 Loading Markdown files…")
    docs = load_markdown_docs()
    print(f"   Loaded {len(docs)} documents")

    print("✂️  Chunking…")
    chunks = chunk_docs(docs)
    print(f"   Produced {len(chunks)} chunks")
    print("********** Chunks *********")
    print(chunks)

    # --- Embeddings ---
    # For OpenAI:
    # embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print(f"💾 Building/Rebuilding_if_exists Chroma at {PERSIST_DIR} …")

    if os.path.isdir(PERSIST_DIR):
      shutil.rmtree(PERSIST_DIR)

    vs = Chroma(collection_name="rag_md",
                embedding_function=embeddings,
                persist_directory=PERSIST_DIR)
    vs.add_documents(chunks)
    vs.persist()

    print("✅ Ingestion complete.")


if __name__ == "__main__":
    main()
