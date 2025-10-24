# RAG_LangChain

A Retrieval-Augmented Generation (RAG) system built with LangChain and ChromaDB for document-based question answering.

## Overview

This project implements a RAG pipeline that:

- Ingests Markdown documents from a dataset
- Creates embeddings using HuggingFace sentence transformers
- Stores vectors in ChromaDB for efficient retrieval
- Provides a conversational interface for querying documents

## Project Structure

```
RAG_LangChain/
├── dataset/
│   ├── raw/                    # Original documents (PDFs, DOCX)
│   └── refined/                # Processed Markdown files
├── .chroma_rag/               # ChromaDB vector store (auto-generated)
├── ingest.py                   # Document ingestion pipeline
├── rag_app.py                  # RAG query interface
├── main.ipynb                  # Jupyter notebook for exploration
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd RAG_LangChain
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

Create a `.env` file in the project root:

```bash
# Optional: Customize these defaults
CHROMA_DIR=.chroma_rag
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=llama3
RAG_TOP_K=5
```

## Usage

### 1. Prepare Your Documents

Place your Markdown files in the `dataset/refined/` directory. The system will automatically process all `.md` files in this folder.

Example structure:

```
dataset/refined/
├── document1.md
├── document2.md
└── subfolder/
    └── document3.md
```

### 2. Ingest Documents

Run the ingestion pipeline to process documents and create the vector store:

```bash
python ingest.py
```

This will:

- Load all Markdown files from `dataset/refined/`
- Split them into chunks (500 chars with 50 char overlap)
- Generate embeddings using HuggingFace's `all-MiniLM-L6-v2` model
- Store vectors in ChromaDB

### 3. Query the RAG System

Start the interactive RAG application:

```bash
python rag_app.py
```

This will start a conversational interface where you can ask questions about your documents.

## Configuration

### Embedding Models

The system uses HuggingFace embeddings by default. To use OpenAI embeddings instead:

1. Set your OpenAI API key in `.env`:

```bash
OPENAI_API_KEY=your_api_key_here
```

2. Modify `ingest.py` to use OpenAI embeddings:

```python
from langchain_openai import OpenAIEmbeddings
embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
```

### Chat Models

The system supports both local and cloud-based LLMs:

**Local (Ollama):**

```python
from langchain_community.chat_models import ChatOllama
llm = ChatOllama(model="llama3", temperature=0.2)
```

**OpenAI:**

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.1)
```

### Retrieval Parameters

- `RAG_TOP_K`: Number of document chunks to retrieve (default: 5)
- `chunk_size`: Size of document chunks (default: 500 characters)
- `chunk_overlap`: Overlap between chunks (default: 50 characters)

## Key Features

- **Document Processing**: Automatically handles Markdown files with code blocks
- **Smart Chunking**: Uses markdown-aware separators for optimal chunking
- **Diverse Retrieval**: Uses MMR (Maximal Marginal Relevance) for diverse results
- **Source Citation**: Provides source file references in responses
- **Local & Cloud Support**: Works with both local and cloud-based models

## Dependencies

Key packages:

- `langchain`: Core framework for RAG pipeline
- `langchain-community`: Community integrations
- `chromadb`: Vector database
- `sentence-transformers`: HuggingFace embeddings
- `unstructured`: Document processing
- `python-dotenv`: Environment variable management

## Troubleshooting

### Common Issues

1. **Missing documents**: Ensure `dataset/refined/` contains `.md` files
2. **ChromaDB errors**: Delete `.chroma_rag/` folder and re-run `ingest.py`
3. **Model download**: First run may take time to download embedding models
4. **Memory issues**: Reduce `chunk_size` or `RAG_TOP_K` for large documents

### Performance Tips

- Use SSD storage for better ChromaDB performance
- Adjust `chunk_size` based on your document types
- Consider using GPU for faster embedding generation
- Monitor memory usage with large document collections

## License

See `LICENSE` file for details.
