"""
Embedding providers for Wiki RAG semantic search.

Tiered architecture:
1. LocalEmbeddingProvider — sentence-transformers (DEPLOYMENT_MODE=full only)
2. GeminiEmbeddingProvider — Google Generative AI SDK (free tier)
3. OpenAIEmbeddingProvider — any OpenAI-compatible API (httpx)

BM25 remains as fallback when no embedding provider is available.
"""

import logging
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    dimension: int = 0
    model_name: str = ""

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of vectors."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string. Returns one vector."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name for stats/logging."""
        ...


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """
    Google Gemini embedding via REST API (httpx).

    Uses httpx instead of genai SDK to avoid gRPC proxy conflicts when
    GeminiProvider for LLM sets global HTTP_PROXY env vars for VLESS.

    Model: text-embedding-004 (768 dims, free tier 1500 req/min).
    Batch: up to 100 texts per call.
    """

    API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str):
        import httpx

        # Don't use proxy for embedding requests (LLM GeminiProvider sets proxy globally)
        self._client = httpx.Client(timeout=60.0, proxy=None)
        self._api_key = api_key
        self.model_name = "text-embedding-004"
        self.dimension = 768
        logger.info(f"GeminiEmbeddingProvider initialized: {self.model_name} (REST API)")

    def _call_api(self, texts: list[str], task_type: str) -> list[list[float]]:
        url = f"{self.API_URL}/{self.model_name}:batchEmbedContents"
        requests = [
            {
                "model": f"models/{self.model_name}",
                "content": {"parts": [{"text": t}]},
                "taskType": task_type,
            }
            for t in texts
        ]
        payload = {"requests": requests}

        response = self._client.post(url, json=payload, params={"key": self._api_key})
        response.raise_for_status()
        data = response.json()

        return [item["values"] for item in data["embeddings"]]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            results.extend(self._call_api(batch, "RETRIEVAL_DOCUMENT"))
        return results

    def embed_query(self, text: str) -> list[float]:
        vectors = self._call_api([text], "RETRIEVAL_QUERY")
        return vectors[0]

    def provider_name(self) -> str:
        return "gemini"


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """
    OpenAI-compatible embedding API via httpx.

    Works with: OpenAI, DeepSeek, OpenRouter, any /v1/embeddings endpoint.
    """

    def __init__(self, api_key: str, base_url: str, model: str = "text-embedding-3-small"):
        import httpx

        self._client = httpx.Client(timeout=60.0)
        self._api_key = api_key
        # Ensure base_url doesn't end with /v1 (we add it ourselves)
        self._base_url = base_url.rstrip("/").removesuffix("/v1")
        self.model_name = model
        self.dimension = 0  # determined from first response
        logger.info(
            f"OpenAIEmbeddingProvider initialized: {self._base_url} model={self.model_name}"
        )

    def _call_api(self, input_texts: list[str]) -> list[list[float]]:
        url = f"{self._base_url}/v1/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }
        payload = {"input": input_texts, "model": self.model_name}

        response = self._client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Sort by index to maintain order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        vectors = [e["embedding"] for e in embeddings]

        if vectors and self.dimension == 0:
            self.dimension = len(vectors[0])

        return vectors

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            results.extend(self._call_api(batch))
        return results

    def embed_query(self, text: str) -> list[float]:
        vectors = self._call_api([text])
        return vectors[0]

    def provider_name(self) -> str:
        return "openai"


# Optional local embeddings — requires sentence-transformers
LOCAL_EMBEDDINGS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer

    LOCAL_EMBEDDINGS_AVAILABLE = True
except ImportError:
    pass


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Local embedding via sentence-transformers.

    Model: paraphrase-multilingual-MiniLM-L12-v2 (~420MB, 384 dims).
    Best quality for Russian/English. Only loads when package is installed.
    """

    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

    def __init__(self, model_name: str | None = None):
        if not LOCAL_EMBEDDINGS_AVAILABLE:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )

        self.model_name = model_name or self.DEFAULT_MODEL
        # Determine device
        device = "cpu"
        try:
            import torch

            if torch.cuda.is_available():
                device = "cuda"
        except ImportError:
            pass

        self._model = SentenceTransformer(self.model_name, device=device)
        self.dimension = self._model.get_sentence_embedding_dimension()
        logger.info(
            f"LocalEmbeddingProvider initialized: {self.model_name} "
            f"(dim={self.dimension}, device={device})"
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
        return [vec.tolist() for vec in embeddings]

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode(text, show_progress_bar=False, convert_to_numpy=True)
        return embedding.tolist()

    def provider_name(self) -> str:
        return "local"
