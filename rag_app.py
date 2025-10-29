import os
import math
import textwrap
from typing import List, Tuple, Dict, Any, Optional

from dotenv import load_dotenv

# Vector store + embeddings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# LLMs (pick via env)
from langchain_openai import ChatOpenAI  # if using OpenAI
from langchain_community.chat_models import ChatOllama  # if using Ollama

# Prompting
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# (Optional) cross-encoder reranker
try:
    from sentence_transformers import CrossEncoder
    _HAS_RERANKER = True
except Exception:
    _HAS_RERANKER = False


load_dotenv()

# ----------------------------
# Config
# ----------------------------
PERSIST_DIR = os.getenv("CHROMA_DIR", ".chroma_rag")
COLLECTION = os.getenv("CHROMA_COLLECTION", "rag_docs")

# Retrieval knobs
# final k after post selection
TOP_K = int(os.getenv("RAG_TOP_K", "6"))
FETCH_K = int(os.getenv("RAG_FETCH_K", "24"))     # initial wider fetch
# 0..1 (higher=stricter)
SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.18"))

# Models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
DEVICE = os.getenv("DEVICE", "cpu")  # or "cuda"
# for OpenAI; or "llama3" for Ollama
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
USE_OLLAMA = os.getenv("USE_OLLAMA", "0") == "1"

# Optional reranker model (cross-encoder)
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
USE_RERANKER = os.getenv("USE_RERANKER", "1") == "1" and _HAS_RERANKER

# Minimum context length guard (if too low, answer with “insufficient context”)
MIN_CONTEXT_CHARS = int(os.getenv("MIN_CONTEXT_CHARS", "600"))

# ----------------------------
# Embeddings & VectorStore
# ----------------------------
emb = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": DEVICE},
    encode_kwargs={"normalize_embeddings": True},  # BGE best practice
)

db = Chroma(
    collection_name=COLLECTION,
    embedding_function=emb,
    persist_directory=PERSIST_DIR,
)

# ----------------------------
# (Optional) Cross-encoder reranker
# ----------------------------
reranker: Optional[CrossEncoder] = None
if USE_RERANKER:
    try:
        reranker = CrossEncoder(RERANKER_MODEL, device=DEVICE)
        print(f"🔁 Using reranker: {RERANKER_MODEL}")
    except Exception as e:
        print(f"[WARN] Could not init reranker {RERANKER_MODEL}: {e}")
        reranker = None

# ----------------------------
# LLM
# ----------------------------
if USE_OLLAMA:
    llm = ChatOllama(model=CHAT_MODEL, temperature=0.2)
    print(f"🧠 Using Ollama model: {CHAT_MODEL}")
else:
    # Expect OPENAI_API_KEY in env
    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0.2)
    print(f"🧠 Using OpenAI model: {CHAT_MODEL}")

# ----------------------------
# Prompt
# ----------------------------
SYSTEM_PROMPT = """\
You are a careful, **grounded** assistant specialized in the EJAR–SEC domain.
Answer **only** from the provided CONTEXT. If the answer is not in CONTEXT, say:
“I don’t have enough information in the provided EJAR–SEC corpus to answer that.”

Rules:
- Prefer precise, concise language using the domain’s terms (EJAR, SEC, SAP IS-U, Move-In/Move-Out).
- Do not introduce unrelated meanings for abbreviations.
- If you synthesize or paraphrase, ensure it is **strictly faithful** to the context.
- Add a short “Sources” section listing the unique source paths you used.
"""

USER_PROMPT = """\
Question:
{question}

CONTEXT (RAG):
{context}
"""

prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", USER_PROMPT)]
)
parser = StrOutputParser()

# ----------------------------
# Retrieval utils
# ----------------------------


def _prefix_bge_query(q: str) -> str:
    q = q.strip()
    # add BGE query prefix if missing
    return q if q.lower().startswith("query:") else f"query: {q}"


def similarity_search_with_scores(query: str, k: int, fetch_k: int) -> List[Tuple[Any, float]]:
    """
    Returns list of (Document, score). `score` is relevance in 0..1 (higher=more relevant).
    """
    # use larger fetch then truncate; include scores
    results = db.similarity_search_with_relevance_scores(query, k=fetch_k)
    # filter by threshold
    results = [(doc, score) for (doc, score) in results if (
        score is None or score >= SCORE_THRESHOLD)]
    # post-select using simple MMR-like diversity by section/source (lightweight)
    return _post_select_diverse(results, top_k=k)


def _post_select_diverse(results: List[Tuple[Any, float]], top_k: int) -> List[Tuple[Any, float]]:
    """
    Light diversity: avoid same doc/source repeating too much.
    """
    selected: List[Tuple[Any, float]] = []
    seen_chunk_ids = set()
    seen_sources = set()
    for doc, score in sorted(results, key=lambda x: (x[1] or 0), reverse=True):
        cid = doc.metadata.get("chunk_id")
        src = doc.metadata.get("source")
        # allow up to 2 chunks per source
        if cid in seen_chunk_ids:
            continue
        if list(s for s in selected if s[0].metadata.get("source") == src).__len__() >= 2:
            continue
        selected.append((doc, score))
        seen_chunk_ids.add(cid)
        seen_sources.add(src)
        if len(selected) >= top_k:
            break
    if len(selected) < top_k:
        # backfill if needed
        for doc, score in results:
            if (doc, score) in selected:
                continue
            if doc.metadata.get("chunk_id") in seen_chunk_ids:
                continue
            selected.append((doc, score))
            if len(selected) >= top_k:
                break
    return selected[:top_k]


def rerank_if_available(query: str, docs: List[Tuple[Any, float]]) -> List[Tuple[Any, float]]:
    """
    If cross-encoder is available, rerank the current shortlist.
    """
    if not reranker or not docs:
        return docs
    pairs = [[query, d.page_content] for d, _ in docs]
    try:
        scores = reranker.predict(pairs)  # higher = better
        rescored = list(zip([d for d, _ in docs], [float(s) for s in scores]))
        rescored.sort(key=lambda x: x[1], reverse=True)
        return rescored
    except Exception as e:
        print(f"[WARN] Reranker failed: {e}")
        return docs


def build_context(docs: List[Tuple[Any, float]]) -> Tuple[str, List[Dict[str, str]]]:
    """
    Build a readable context blob with source markers and collect sources for citation.
    """
    blocks = []
    used_sources: Dict[str, Dict[str, str]] = {}
    for idx, (d, score) in enumerate(docs, 1):
        src = d.metadata.get("source", "?")
        chunk_id = d.metadata.get(
            "chunk_id") or d.metadata.get("start_index") or "?"
        heading = d.metadata.get(
            "section_path") or d.metadata.get("json_path") or ""
        header_line = f"[S{idx}] source: {src} | chunk: {chunk_id} | {heading}".strip(
        )
        block = f"{header_line}\n{d.page_content}"
        blocks.append(block)
        used_sources.setdefault(src, {"source": src})
    ctx = "\n\n---\n\n".join(blocks)
    return ctx, list(used_sources.values())


def format_sources(sources: List[Dict[str, str]]) -> str:
    lines = []
    for i, s in enumerate(sources, 1):
        lines.append(f"{i}. {s['source']}")
    return "\n".join(lines)

# ----------------------------
# RAG chain
# ----------------------------


def answer_question(q: str) -> str:
    q_bge = _prefix_bge_query(q)

    # 1) retrieve with scores + diversity
    docs_scored = similarity_search_with_scores(
        q_bge, k=TOP_K, fetch_k=FETCH_K)

    # 2) (optional) rerank shortlist
    docs_scored = rerank_if_available(q_bge, docs_scored)

    # 3) build context
    context_text, sources = build_context(docs_scored)

    # 4) guard: insufficient context
    if len(context_text) < MIN_CONTEXT_CHARS or len(docs_scored) == 0:
        return (
            "I don’t have enough information in the provided EJAR–SEC corpus to answer that.\n\n"
            "Sources: (none)"
        )

    # 5) LLM
    msgs = prompt.format_messages(question=q, context=context_text)
    raw = llm.invoke(msgs)
    text = StrOutputParser().invoke(raw)

    # 6) append sources section
    return text.strip() + "\n\nSources:\n" + format_sources(sources)


# ----------------------------
# CLI
# ----------------------------
if __name__ == "__main__":
    print("💬 EJAR–SEC RAG ready. Ask a question (Ctrl+C to exit).")
    try:
        while True:
            q = input("\n>> ").strip()
            if not q:
                continue
            print("\n--- Answer ---")
            print(answer_question(q))
    except KeyboardInterrupt:
        print("\nBye!")
