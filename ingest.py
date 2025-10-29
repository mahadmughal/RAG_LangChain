"""Document ingestion pipeline for RAG system using LangChain and Chroma (Markdown + JSON)."""
import os
import re
import json
import shutil
import hashlib
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Tuple, Iterable

from dotenv import load_dotenv

from langchain.schema import Document
from langchain_community.document_loaders import DirectoryLoader, UnstructuredMarkdownLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter,
)

# ----------------------------
# Config
# ----------------------------
load_dotenv()
DATA_DIR = Path("dataset/refined")
PERSIST_DIR = os.getenv("CHROMA_DIR", ".chroma_rag")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "rag_docs")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
MIN_CHARS = int(os.getenv("MIN_CHARS", "120"))  # drop very tiny chunks

# ----------------------------
# Chroma-safe metadata sanitizer (flat scalars only)
# ----------------------------
ALLOWED_META_SCALARS = (str, int, float, bool, type(None))


def _to_scalar(v: Any) -> Any:
    """Return a Chroma-safe scalar. Non-scalars -> JSON string."""
    if isinstance(v, ALLOWED_META_SCALARS):
        return v
    try:
        return json.dumps(v, ensure_ascii=False)
    except Exception:
        return str(v)


def sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all metadata values to scalars. Keys become strings."""
    if not isinstance(meta, dict):
        return {"meta": _to_scalar(meta)}
    return {str(k): _to_scalar(v) for k, v in meta.items()}


# ----------------------------
# Text hygiene
# ----------------------------
def clean_text(s: str) -> str:
    if not s:
        return s
    # normalize unicode, collapse excessive whitespace, keep code blocks intact
    s = unicodedata.normalize("NFC", s)
    # light whitespace cleanup but avoid killing newlines inside code blocks
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def ensure_passage_prefix(content: str, ctx: str = "CTX") -> str:
    c = content.lstrip()
    if not c.lower().startswith("passage:"):
        return f"passage: [CTX] {ctx}\n{content}"
    return content


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# ----------------------------
# JSON -> path-aware passages
# ----------------------------
TEXT_CANDIDATE_FIELDS = ("content", "text", "body",
                         "message", "description", "summary", "markdown")


def json_walk(obj: Any, path: str = "") -> Iterable[Tuple[str, Any]]:
    """Yield (json_path, value) for all leaves; keep lists indexed."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            yield from json_walk(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{path}[{i}]"
            yield from json_walk(v, p)
    else:
        yield path, obj


def pick_text_field(d: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """Choose a prime text field; else serialize a compact narrative from leaves."""
    for k in TEXT_CANDIDATE_FIELDS:
        if k in d and isinstance(d[k], (str, int, float)):
            text = str(d[k])
            meta = {kk: vv for kk, vv in d.items() if kk != k}
            return text, meta

    # Build a readable narrative from scalar leaves (path: value)
    lines: List[str] = []
    for p, v in json_walk(d):
        if isinstance(v, (str, int, float, bool)) and v not in (None, ""):
            pretty_p = p.replace(".", " › ").replace(
                "[", " [").replace("]", " ]")
            lines.append(f"{pretty_p}: {v}")
    if lines:
        return "\n".join(lines), {}

    # fallback: compact JSON
    return json.dumps(d, ensure_ascii=False), {}


def json_to_documents(path: Path) -> List[Document]:
    """Turn arbitrary JSON (array/object/primitive) into passage-ized Documents."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[WARN] Failed to parse JSON: {path} ({e}); skipping.")
        return []

    docs: List[Document] = []

    def mk_doc(text: str, meta: Dict[str, Any]) -> Document:
        meta = dict(meta or {})
        meta["source"] = str(path)
        meta["doc_type"] = "json"
        meta["domain"] = "ejar-sec"
        meta = sanitize_metadata(meta)
        text = clean_text(text)
        # Add bge prefix with json_path (if present)
        ctx = meta.get("json_path") or meta.get(
            "title") or Path(str(path)).name
        page = ensure_passage_prefix(text, ctx)
        return Document(page_content=page, metadata=meta)

    if isinstance(data, list):
        for idx, item in enumerate(data):
            if isinstance(item, dict):
                # Prefer a textual field; also include path-aware leaves
                text, meta = pick_text_field(item)
                meta.update({"json_index": idx, "title": item.get("title")})
                doc = mk_doc(text, meta)
                docs.append(doc)

                # Optional: add fine-grained leaf docs for precision (enable if you want more atomicity)
                for p, v in json_walk(item):
                    if isinstance(v, (str, int, float, bool)):
                        meta_leaf = {"json_index": idx,
                                     "json_path": p, "title": item.get("title")}
                        docs.append(mk_doc(f"{p}: {v}", meta_leaf))
            else:
                docs.append(mk_doc(str(item), {"json_index": idx}))
    elif isinstance(data, dict):
        text, meta = pick_text_field(data)
        docs.append(mk_doc(text, meta))
    else:
        docs.append(mk_doc(str(data), {}))

    return docs


# ----------------------------
# Markdown loading (header-aware)
# ----------------------------
def load_markdown_docs() -> List[Document]:
    md_loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        show_progress=True,
        use_multithreading=True,
    )
    raw_docs = md_loader.load()
    docs: List[Document] = []

    # Split by headers first for better breadcrumbs
    for d in raw_docs:
        source = (
            d.metadata.get("source")
            or d.metadata.get("filename")
            or str(d.metadata.get("path") or "unknown.md")
        )

        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")]
        )
        # header_splitter expects plain text; build a temp doc list
        parts = header_splitter.split_text(d.page_content)

        # propagate metadata and add breadcrumbs
        for p in parts:
            section_path = " > ".join(
                [p.metadata.get("h1", ""), p.metadata.get(
                    "h2", ""), p.metadata.get("h3", "")]
            ).strip(" >") or "ROOT"
            meta = {
                "source": source,
                "doc_type": "markdown",
                "domain": "ejar-sec",
                "section_path": section_path,
            }
            meta = sanitize_metadata(meta)
            content = clean_text(p.page_content)
            # bge passage prefix with breadcrumb
            page = ensure_passage_prefix(content, section_path)
            docs.append(Document(page_content=page, metadata=meta))

    return docs


# ----------------------------
# Unified loader for .md + .json
# ----------------------------
def load_docs() -> List[Document]:
    docs: List[Document] = []

    md_docs = load_markdown_docs()
    docs.extend(md_docs)

    json_count = 0
    for json_path in DATA_DIR.rglob("*.json"):
        if json_path.is_file():
            jdocs = json_to_documents(json_path)
            json_count += len(jdocs)
            docs.extend(jdocs)

    print(
        f"   Loaded {len(md_docs)} markdown chunks and {json_count} json chunks")
    return docs


# ----------------------------
# Chunking & enrichment
# ----------------------------
def chunk_docs(docs: List[Document]) -> List[Document]:
    """
    Secondary recursive chunking (post header/json passage creation).
    Keeps chunks ~1000 chars, overlaps 100, preserves code fences.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n```", "\n# ", "\n## ", "\n### ", "\n- ", "\n", " ", ""],
        length_function=len,
        add_start_index=True,
    )
    chunks = splitter.split_documents(docs)

    # filter too-small chunks (often headings only)
    chunks = [c for c in chunks if len(c.page_content) >= MIN_CHARS]

    # add stable provenance & scalar-only metadata
    by_source: Dict[str, List[Document]] = {}
    for c in chunks:
        src = c.metadata.get("source", "unknown")
        by_source.setdefault(src, []).append(c)

    for src, group in by_source.items():
        group.sort(key=lambda d: d.metadata.get("start_index", 0))
        did = sha1(src)
        n = len(group)
        for i, g in enumerate(group, 1):
            g.metadata.update(
                {
                    "doc_id": did,
                    "chunk_id": f"{did}:{i}/{n}",
                    "chunk_index": i - 1,
                    "n_chunks": n,
                }
            )
            g.metadata = sanitize_metadata(g.metadata)
            # Make sure passage prefix survived after secondary split
            ctx = g.metadata.get("section_path") or g.metadata.get(
                "json_path") or Path(src).name
            g.page_content = ensure_passage_prefix(
                clean_text(g.page_content), ctx)

    return chunks


# ----------------------------
# Main
# ----------------------------
def main():
    if not DATA_DIR.exists():
        raise SystemExit(
            f"Missing {DATA_DIR}/ — add your .md/.json files there.")

    print("📥 Loading documents (.md + .json)…")
    docs = load_docs()
    print(f"   Total loaded docs: {len(docs)}")

    print("✂️  Chunking…")
    chunks = chunk_docs(docs)
    print(f"   Produced {len(chunks)} chunks")

    # --- Embeddings ---
    emb = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": os.getenv("DEVICE", "cpu")},  # or "cuda"
        encode_kwargs={"normalize_embeddings": True},  # bge best practice
    )

    print(f"💾 Building/Rebuilding Chroma at {PERSIST_DIR} …")
    if os.path.isdir(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
        print("🧹 Cleaned existing Chroma directory")

    vs = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=emb,
        persist_directory=PERSIST_DIR,
    )
    vs.add_documents(chunks)
    vs.persist()

    print("✅ Ingestion complete.")
    # Optional: print 3 example chunk ids for sanity
    for c in chunks[:3]:
        print(f"• {c.metadata.get('source')} :: {c.metadata.get('chunk_id')}")


if __name__ == "__main__":
    main()
