import os
from dotenv import load_dotenv

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings  # matches your ingest
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Choose an LLM: OpenAI or Ollama (local). Pick ONE block.

# A) OpenAI (cloud)
# from langchain_openai import ChatOpenAI
# B) Ollama (local)
from langchain_community.chat_models import ChatOllama

load_dotenv()
PERSIST_DIR = os.getenv("CHROMA_DIR", ".chroma_rag")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3")  # or "llama3" for Ollama
K = int(os.getenv("RAG_TOP_K", "5"))

# Same embedder as ingest.py to avoid cosine-space mismatch
emb = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    encode_kwargs={"normalize_embeddings": True},
)

db = Chroma(
    collection_name="rag_md",
    embedding_function=emb,
    persist_directory=PERSIST_DIR
)

# Retriever: try mmr for diversity
retriever = db.as_retriever(search_type="mmr", search_kwargs={"k": K, "fetch_k": max(20, 4*K), "lambda_mult": 0.5})

# Pick your LLM
# llm = ChatOpenAI(model=CHAT_MODEL, temperature=0.1)
llm = ChatOllama(model=CHAT_MODEL, temperature=0.2)  # e.g., CHAT_MODEL="llama3"

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You answer using ONLY the provided context. If unsure, say you don't know. "
     "Cite the source filenames when possible."),
    ("human", "Question: {question}\n\nContext:\n{context}")
])

def format_docs(docs):
    return "\n\n---\n\n".join(
        f"[source: {d.metadata.get('source','?')} @ {d.metadata.get('start_index','?')}]\n{d.page_content}"
        for d in docs
    )

chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

if __name__ == "__main__":
    print("💬 RAG ready. Ask a question (Ctrl+C to exit).")
    try:
        while True:
            q = input("\n>> ")
            if not q.strip(): 
                continue
            print("\n--- Answer ---")
            print(chain.invoke(q))
    except KeyboardInterrupt:
        print("\nBye!")
