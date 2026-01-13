import math
import re
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel

DEFAULT_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge_base.txt"


class KBEntry(BaseModel):
    id: int
    title: str
    body: str
    tags: List[str] = []


class ScoredItem(BaseModel):
    entry: KBEntry
    score: float


class AskResponse(BaseModel):
    items: List[ScoredItem]
    answer: Optional[str] = None
    llm_provider: Optional[str] = None


_default_index: Optional[dict] = None
_custom_index: Optional[dict] = None

_tag_re = re.compile(r"#([^#\s]+)")
_word_re = re.compile(r"[а-яА-Яa-zA-Z0-9_]+")


def _tokenize(text: str) -> List[str]:
    return _word_re.findall(text.lower())


def _vectorize(text: str) -> Dict[str, float]:
    tokens = _tokenize(text)
    freq: Dict[str, float] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0.0) + 1.0
    return freq


def _norm(vec: Dict[str, float]) -> float:
    return math.sqrt(sum(v * v for v in vec.values())) or 1.0


def _cosine(q_vec: Dict[str, float], q_norm: float, d_vec: Dict[str, float], d_norm: float) -> float:
    dot = sum(q_vec.get(t, 0) * d_vec.get(t, 0) for t in q_vec)
    return dot / (q_norm * d_norm) if dot else 0.0


def _build_index(text: str) -> dict:
    blocks = [b.strip() for b in text.split("##") if b.strip()]
    entries, vectors, norms = [], [], []

    for idx, block in enumerate(blocks, 1):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        title = lines[0]
        body = "\n".join(lines[1:])
        tags = _tag_re.findall(block)

        entry = KBEntry(id=idx, title=title, body=body, tags=tags)
        vec = _vectorize(block)

        entries.append(entry)
        vectors.append(vec)
        norms.append(_norm(vec))

    if not entries:
        raise ValueError("Не найдено блоков в базе знаний (разделитель '##')")

    return {"entries": entries, "vectors": vectors, "norms": norms}


def _ensure_default_loaded():
    global _default_index
    if _default_index is None:
        if not DEFAULT_KB_PATH.exists():
            raise RuntimeError(f"Файл не найден: {DEFAULT_KB_PATH}")
        _default_index = _build_index(DEFAULT_KB_PATH.read_text(encoding="utf-8"))


def load_custom_kb_from_text(text: str) -> int:
    global _custom_index
    _custom_index = _build_index(text)
    return len(_custom_index["entries"])


def reset_custom_kb():
    global _custom_index
    _custom_index = None


def search_similar(question: str, top_k: int = 3, use_custom: bool = False) -> AskResponse:
    _ensure_default_loaded()
    index = _custom_index if (use_custom and _custom_index) else _default_index

    q_vec = _vectorize(question)
    q_norm = _norm(q_vec)

    scored = []
    for entry, d_vec, d_norm in zip(index["entries"], index["vectors"], index["norms"]):
        score = _cosine(q_vec, q_norm, d_vec, d_norm)
        if score > 0:
            scored.append(ScoredItem(entry=entry, score=score))

    scored.sort(key=lambda x: x.score, reverse=True)
    return AskResponse(items=scored[:top_k])


try:
    _ensure_default_loaded()
except Exception as e:
    print(f"[kb] Ошибка загрузки базы: {e}")
