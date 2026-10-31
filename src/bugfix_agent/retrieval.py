"""Small dependency-free BM25 retriever for Python source files."""
from __future__ import annotations
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d+")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "build", "dist", "node_modules", "site-packages"}

def _tokens(text: str) -> list[str]:
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return [part.lower() for token in TOKEN_RE.findall(normalized) for part in token.split("_") if part]

@dataclass(frozen=True)
class CodeChunk:
    path: str
    start_line: int
    end_line: int
    text: str
    @property
    def tokens(self) -> list[str]:
        return _tokens(self.text)

def collect_chunks(root: Path, chunk_lines: int = 80, overlap: int = 12) -> list[CodeChunk]:
    """Read Python files into stable, line-addressable chunks."""
    if chunk_lines < 1 or overlap < 0 or overlap >= chunk_lines:
        raise ValueError("Require chunk_lines > overlap >= 0.")
    chunks: list[CodeChunk] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        step = chunk_lines - overlap
        for start in range(0, len(lines), step):
            end = min(start + chunk_lines, len(lines))
            content = "\n".join(lines[start:end]).strip()
            if content:
                chunks.append(CodeChunk(path.relative_to(root).as_posix(), start + 1, end, content))
            if end == len(lines):
                break
    return chunks

def retrieve(query: str, chunks: list[CodeChunk], limit: int = 6) -> list[tuple[CodeChunk, float]]:
    """Rank chunks with BM25; return score-descending results with stable ties."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    query_terms = _tokens(query)
    if not query_terms or not chunks:
        return []
    tokenized = [chunk.tokens for chunk in chunks]
    average_length = sum(map(len, tokenized)) / len(tokenized) or 1.0
    document_frequency: Counter[str] = Counter()
    for tokens in tokenized:
        document_frequency.update(set(tokens))
    total = len(chunks)
    k1, b = 1.5, 0.75
    ranked: list[tuple[CodeChunk, float, int]] = []
    for index, (chunk, tokens) in enumerate(zip(chunks, tokenized)):
        counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            frequency = counts[term]
            if not frequency:
                continue
            inverse_frequency = math.log(1 + (total - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + k1 * (1 - b + b * len(tokens) / average_length)
            score += inverse_frequency * frequency * (k1 + 1) / denominator
        if score > 0:
            ranked.append((chunk, score, index))
    ranked.sort(key=lambda item: (-item[1], item[0].path, item[0].start_line, item[2]))
    return [(chunk, score) for chunk, score, _ in ranked[:limit]]
