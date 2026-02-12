"""
Lightweight Wiki RAG service — retrieves relevant wiki sections for user queries.

Uses BM25 Okapi scoring with Russian/English stemming. Parses wiki-pages/*.md
on startup, builds an inverted index, and returns top-k relevant sections
formatted as context for LLM system prompt injection.

Works offline, zero GPU, zero API keys.
"""

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import snowballstemmer


logger = logging.getLogger(__name__)

# Stemmers — singleton per language
_ru_stemmer = snowballstemmer.stemmer("russian")
_en_stemmer = snowballstemmer.stemmer("english")

# BM25 Okapi parameters
BM25_K1 = 1.5  # term frequency saturation
BM25_B = 0.75  # document length normalization
MIN_SCORE = 0.5  # ignore garbage matches

# Базовые стоп-слова (русские + английские) — фильтруем шум из запросов
STOP_WORDS = frozenset(
    {
        # Russian
        "и",
        "в",
        "на",
        "с",
        "по",
        "для",
        "что",
        "как",
        "это",
        "не",
        "из",
        "к",
        "от",
        "за",
        "до",
        "или",
        "но",
        "а",
        "о",
        "у",
        "же",
        "ли",
        "бы",
        "то",
        "все",
        "так",
        "его",
        "мне",
        "мой",
        "уже",
        "при",
        "про",
        "ещё",
        "еще",
        "нет",
        "да",
        "вот",
        "тут",
        "там",
        "где",
        "кто",
        "чем",
        "вы",
        "мы",
        "он",
        "она",
        "они",
        # English
        "the",
        "is",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "a",
        "an",
        "it",
        "by",
        "with",
        "as",
        "be",
        "are",
        "was",
        "do",
        "if",
        "no",
        "not",
        "how",
        "what",
        "this",
        "that",
    }
)

# Минимальная длина токена для индексации
MIN_TOKEN_LEN = 2


def _is_cyrillic(word: str) -> bool:
    """Check if word contains Cyrillic characters."""
    return any("\u0400" <= ch <= "\u04ff" for ch in word)


def _stem(word: str) -> str:
    """Stem a single word using the appropriate language stemmer."""
    if _is_cyrillic(word):
        return _ru_stemmer.stemWord(word)
    return _en_stemmer.stemWord(word)


@dataclass
class WikiSection:
    """One indexed section from a wiki page."""

    title: str
    body: str
    source_file: str
    tokens: Counter = field(default_factory=Counter)


class WikiRAGService:
    """Retrieves relevant wiki sections for user queries via BM25 scoring."""

    def __init__(self, wiki_dir: Optional[Path] = None):
        self.sections: list[WikiSection] = []
        self.doc_freqs: Counter = Counter()
        self.avg_dl: float = 0.0
        self.total_docs: int = 0
        self._files_indexed: int = 0

        if wiki_dir and wiki_dir.exists():
            self._load_and_index(wiki_dir)

    def _tokenize(self, text: str) -> list[str]:
        """Unicode-aware tokenization with stemming — works with Cyrillic."""
        tokens = re.findall(r"\w+", text.lower())
        return [_stem(t) for t in tokens if len(t) >= MIN_TOKEN_LEN and t not in STOP_WORDS]

    def _split_md_by_headers(self, content: str) -> list[tuple[str, str]]:
        """Split markdown by ## and ### headers. Returns (header, body) pairs."""
        sections = []
        pattern = r"^(#{2,3})\s+(.+?)$"
        current_header = ""
        current_body: list[str] = []

        for line in content.split("\n"):
            match = re.match(pattern, line)
            if match:
                if current_header and current_body:
                    sections.append((current_header, "\n".join(current_body)))
                current_header = match.group(2).strip()
                current_body = []
            else:
                current_body.append(line)

        if current_header and current_body:
            sections.append((current_header, "\n".join(current_body)))

        return sections

    def _load_and_index(self, wiki_dir: Path) -> None:
        """Parse all .md files in wiki_dir, build BM25 index."""
        self.sections = []
        self.doc_freqs = Counter()
        total_tokens = 0

        md_files = sorted(wiki_dir.glob("*.md"))
        files_processed = 0

        for md_file in md_files:
            if md_file.name.startswith("_"):
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Wiki RAG: не удалось прочитать {md_file.name}: {e}")
                continue

            raw_sections = self._split_md_by_headers(content)
            files_processed += 1

            for title, body in raw_sections:
                body_stripped = body.strip()
                if len(body_stripped) < 50:
                    continue

                # Токенизируем заголовок + тело (заголовок весомее — 4x boost)
                text = f"{title} {title} {title} {title} {body_stripped}"
                tokens = Counter(self._tokenize(text))

                section = WikiSection(
                    title=title,
                    body=body_stripped,
                    source_file=md_file.stem,
                    tokens=tokens,
                )
                self.sections.append(section)

                # Обновляем document frequency
                for token in tokens:
                    self.doc_freqs[token] += 1

                total_tokens += sum(tokens.values())

        # BM25 stats
        self.total_docs = len(self.sections)
        self.avg_dl = total_tokens / self.total_docs if self.total_docs > 0 else 1.0

        self._files_indexed = files_processed
        logger.info(
            f"📚 Wiki RAG (BM25): проиндексировано {self.total_docs} секций "
            f"из {files_processed} файлов, "
            f"{len(self.doc_freqs)} уникальных стемов, "
            f"avg_dl={self.avg_dl:.1f}"
        )

    def _bm25_score(self, query_tokens: list[str], section: WikiSection) -> float:
        """Compute BM25 Okapi score for a section against query tokens."""
        score = 0.0
        doc_len = sum(section.tokens.values())
        for token in query_tokens:
            if token not in section.tokens:
                continue
            tf = section.tokens[token]
            df = self.doc_freqs.get(token, 0)
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf_norm = (tf * (BM25_K1 + 1)) / (
                tf + BM25_K1 * (1 - BM25_B + BM25_B * doc_len / self.avg_dl)
            )
            score += idf * tf_norm
        return score

    def retrieve(self, query: str, top_k: int = 3, max_chars: int = 2500) -> str:
        """
        Find top_k relevant sections for query.

        Returns formatted markdown context string, or empty string if no match.
        """
        if not self.sections or not query.strip():
            return ""

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return ""

        # Score each section
        scored: list[tuple[float, WikiSection]] = []
        for section in self.sections:
            score = self._bm25_score(query_tokens, section)
            if score >= MIN_SCORE:
                scored.append((score, section))

        if not scored:
            return ""

        # Sort by score descending, take top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        top_sections = scored[:top_k]

        # Format context, respect max_chars
        parts: list[str] = ["[Документация по теме:]"]
        total_chars = len(parts[0])

        for _score, section in top_sections:
            header_line = f"\n\n## {section.title} ({section.source_file})"
            body = section.body
            # Truncate individual section if needed
            available = max_chars - total_chars - len(header_line) - 4
            if available <= 0:
                break
            if len(body) > available:
                body = body[:available] + "..."

            part = f"{header_line}\n{body}"
            parts.append(part)
            total_chars += len(part)

            if total_chars >= max_chars:
                break

        return "".join(parts) if len(parts) > 1 else ""

    def reload(self, wiki_dir: Path) -> dict:
        """Re-index wiki from disk."""
        old_count = len(self.sections)
        self._load_and_index(wiki_dir)
        return {
            "previous_sections": old_count,
            "current_sections": len(self.sections),
            "files_indexed": self._files_indexed,
        }

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Structured search results with scores (for API/UI)."""
        if not self.sections or not query.strip():
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scored: list[tuple[float, WikiSection]] = []
        for section in self.sections:
            score = self._bm25_score(query_tokens, section)
            if score >= MIN_SCORE:
                scored.append((score, section))

        if not scored:
            return []

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, section in scored[:top_k]:
            results.append(
                {
                    "title": section.title,
                    "body": section.body[:500],
                    "source_file": section.source_file,
                    "score": round(score, 3),
                }
            )
        return results

    def list_source_files(self) -> list[str]:
        """List unique source files in the index."""
        return sorted({s.source_file for s in self.sections})

    @property
    def stats(self) -> dict:
        """Index statistics."""
        return {
            "engine": "bm25",
            "sections_indexed": len(self.sections),
            "files_indexed": self._files_indexed,
            "unique_tokens": len(self.doc_freqs),
            "avg_doc_length": round(self.avg_dl, 1),
            "available": len(self.sections) > 0,
        }
