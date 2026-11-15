"""Unit tests for EmbeddingService. The OpenAI client is a mock: no real API calls."""

import math
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from openai.types import CreateEmbeddingResponse

from app.services.embedding_service import EmbeddingService, normalize
from app.services.llm_service import LLMRateLimitError, LLMServiceError

FAKE_REQUEST = httpx.Request("POST", "https://fake-llm.test/embeddings")


def length(vector: list[float]) -> float:
    return math.sqrt(sum(x * x for x in vector))


def embedding_response(vectors: list[list[float]], order: list[int] | None = None) -> CreateEmbeddingResponse:
    """Build a realistic SDK response. `order` lets a test shuffle the items."""
    indexes = order if order is not None else list(range(len(vectors)))
    return CreateEmbeddingResponse.model_validate(
        {
            "object": "list",
            "model": "fake-embedder",
            "data": [
                {"object": "embedding", "index": i, "embedding": vectors[i]} for i in indexes
            ],
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        }
    )


def fake_client_echoing_lengths(dimensions: int) -> MagicMock:
    """A client that returns one vector per input text: [len(text), 1, 1, ...]."""
    client = MagicMock()

    def create(model: str, input: list[str], dimensions: int) -> CreateEmbeddingResponse:  # noqa: A002
        return embedding_response([[float(len(text))] + [1.0] * (dimensions - 1) for text in input])

    client.embeddings.create.side_effect = create
    return client


def make_service(client: MagicMock, dimensions: int = 3, batch_size: int = 100) -> EmbeddingService:
    return EmbeddingService(client=client, model="fake-embedder", dimensions=dimensions, batch_size=batch_size)


# --- Happy path ---------------------------------------------------------------

def test_sends_model_dimensions_and_texts() -> None:
    client = fake_client_echoing_lengths(3)

    make_service(client).embed_texts(["hello", "world"])

    client.embeddings.create.assert_called_once_with(
        model="fake-embedder", input=["hello", "world"], dimensions=3
    )


def test_vectors_are_normalized_to_length_one() -> None:
    client = MagicMock()
    client.embeddings.create.return_value = embedding_response([[3.0, 4.0, 0.0]])

    [vector] = make_service(client).embed_texts(["hello"])

    assert vector == pytest.approx([0.6, 0.8, 0.0])  # 3-4-5 triangle: length 5 → 1
    assert length(vector) == pytest.approx(1.0)


def test_results_follow_input_order_even_if_api_shuffles_them() -> None:
    client = MagicMock()
    client.embeddings.create.return_value = embedding_response(
        [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], order=[1, 0]  # API sends item 1 first
    )

    first, second = make_service(client).embed_texts(["first", "second"])

    assert first == pytest.approx([1.0, 0.0, 0.0])
    assert second == pytest.approx([0.0, 1.0, 0.0])


def test_missing_index_zero_from_gemini_is_handled() -> None:
    # Real Gemini behaviour (found by the integration test): the first item has no index.
    response = embedding_response([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    response.data[0].index = None  # type: ignore[assignment]
    client = MagicMock()
    client.embeddings.create.return_value = response

    first, second, third = make_service(client).embed_texts(["a", "b", "c"])

    assert first == pytest.approx([1.0, 0.0, 0.0])
    assert second == pytest.approx([0.0, 1.0, 0.0])
    assert third == pytest.approx([0.0, 0.0, 1.0])


def test_large_input_is_split_into_batches() -> None:
    client = fake_client_echoing_lengths(3)
    texts = [f"text number {i}" for i in range(250)]

    vectors = make_service(client, batch_size=100).embed_texts(texts)

    batch_sizes = [len(call.kwargs["input"]) for call in client.embeddings.create.call_args_list]
    assert batch_sizes == [100, 100, 50]
    assert len(vectors) == 250


def test_embed_query_returns_one_vector() -> None:
    client = fake_client_echoing_lengths(3)

    vector = make_service(client).embed_query("Where is the cat?")

    assert len(vector) == 3
    client.embeddings.create.assert_called_once()


# --- Input validation -------------------------------------------------------------

def test_empty_list_makes_no_api_call() -> None:
    client = MagicMock()

    assert make_service(client).embed_texts([]) == []
    client.embeddings.create.assert_not_called()


def test_blank_text_is_rejected_before_calling_the_api() -> None:
    client = MagicMock()

    with pytest.raises(ValueError, match="position 1"):
        make_service(client).embed_texts(["fine", "   "])
    client.embeddings.create.assert_not_called()


# --- Bad responses and errors -------------------------------------------------------

def test_wrong_vector_size_is_an_error() -> None:
    client = MagicMock()
    client.embeddings.create.return_value = embedding_response([[1.0, 2.0]])  # 2, not 3

    with pytest.raises(LLMServiceError, match="Expected 3 numbers"):
        make_service(client, dimensions=3).embed_texts(["hello"])


def test_missing_vectors_are_an_error() -> None:
    client = MagicMock()
    client.embeddings.create.return_value = embedding_response([[1.0, 0.0, 0.0]])  # 1 for 2 texts

    with pytest.raises(LLMServiceError, match="received 1"):
        make_service(client).embed_texts(["one", "two"])


def test_rate_limit_is_translated() -> None:
    client = MagicMock()
    client.embeddings.create.side_effect = openai.RateLimitError(
        message="quota", response=httpx.Response(429, request=FAKE_REQUEST), body=None
    )

    with pytest.raises(LLMRateLimitError):
        make_service(client).embed_texts(["hello"])


def test_all_zero_vector_cannot_be_normalized() -> None:
    with pytest.raises(LLMServiceError, match="all-zero"):
        normalize([0.0, 0.0, 0.0])
