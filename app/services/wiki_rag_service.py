"""
Lightweight Wiki RAG service — retrieves relevant wiki sections for user queries.

Uses TF-IDF-like scoring with no external dependencies. Parses wiki-pages/*.md
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


logger = logging.getLogger(__name__)

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


@dataclass
class WikiSection:
    """One indexed section from a wiki page."""

    title: str
    body: str
    source_file: str
    tokens: Counter = field(default_factory=Counter)


class WikiRAGService:
    """Retrieves relevant wiki sections for user queries via TF-IDF scoring."""

    def __init__(self, wiki_dir: Optional[Path] = None):
        self.sections: list[WikiSection] = []
        self.idf: dict[str, float] = {}
        self._files_indexed: int = 0

        if wiki_dir and wiki_dir.exists():
            self._load_and_index(wiki_dir)

    def _tokenize(self, text: str) -> list[str]:
        """Unicode-aware tokenization — works with Cyrillic."""
        tokens = re.findall(r"\w+", text.lower())
        return [t for t in tokens if len(t) >= MIN_TOKEN_LEN and t not in STOP_WORDS]

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
        """Parse all .md files in wiki_dir, build TF-IDF index."""
        self.sections = []
        doc_freq: Counter = Counter()

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

                # Токенизируем заголовок + тело (заголовок весомее — дублируем)
                text = f"{title} {title} {body_stripped}"
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
                    doc_freq[token] += 1

        # Вычисляем IDF
        n = len(self.sections)
        if n > 0:
            self.idf = {token: math.log(n / df) for token, df in doc_freq.items()}

        self._files_indexed = files_processed
        logger.info(
            f"📚 Wiki RAG: проиндексировано {len(self.sections)} секций "
            f"из {files_processed} файлов, {len(self.idf)} уникальных токенов"
        )

    def retrieve(self, query: str, top_k: int = 3, max_chars: int = 1500) -> str:
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
            score = 0.0
            for token in query_tokens:
                if token in section.tokens:
                    tf = section.tokens[token]
                    idf = self.idf.get(token, 0.0)
                    score += tf * idf
            if score > 0:
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

    @property
    def stats(self) -> dict:
        """Index statistics."""
        return {
            "sections_indexed": len(self.sections),
            "files_indexed": self._files_indexed,
            "unique_tokens": len(self.idf),
            "available": len(self.sections) > 0,
        }
