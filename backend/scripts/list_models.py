"""List the Gemini models your API key can use.

Run from the backend folder (venv active):
    python -m scripts.list_models
"""

import httpx

from app.core.config import get_settings

MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def fetch_all_models(api_key: str) -> list[dict]:
    models: list[dict] = []
    page_token: str | None = None

    while True:
        params: dict[str, str | int] = {"pageSize": 1000}
        if page_token:
            params["pageToken"] = page_token

        # The key goes in a header, never in the URL, so it can't leak into logs.
        response = httpx.get(
            MODELS_URL,
            params=params,
            headers={"x-goog-api-key": api_key},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        models.extend(data.get("models", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            return models


def main() -> None:
    settings = get_settings()

    try:
        models = fetch_all_models(settings.llm_api_key.get_secret_value())
    except httpx.HTTPStatusError as error:
        print(f"Request failed: HTTP {error.response.status_code}")
        print(error.response.text)
        return

    chat_models = []
    embedding_models = []
    for model in models:
        model_id = model["name"].removeprefix("models/")
        methods = model.get("supportedGenerationMethods", [])
        label = f"{model_id:<45} {model.get('displayName', '')}"
        if "generateContent" in methods:
            chat_models.append(label)
        if "embedContent" in methods:
            embedding_models.append(label)

    print("CHAT models (use one for LLM_MODEL):")
    for line in sorted(chat_models):
        print("  ", line)

    print("\nEMBEDDING models (we'll use one in Module 03):")
    for line in sorted(embedding_models):
        print("  ", line)


if __name__ == "__main__":
    main()
