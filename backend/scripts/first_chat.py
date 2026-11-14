"""Your first LLM call: send one message to Gemini and print the answer.

Run from the backend folder (venv active):
    python -m scripts.first_chat "What is a token?"
    python -m scripts.first_chat "Write a slogan for a coffee shop" --temperature 1.5
"""

import argparse

import openai
from openai import OpenAI

from app.core.config import get_settings

SYSTEM_PROMPT = (
    "You are Shema AI, a friendly assistant that explains things simply. "
    "Keep answers under 80 words."
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one message to the LLM.")
    parser.add_argument("question", help="What you want to ask the model")
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional. If omitted, the model's own default is used.",
    )
    args = parser.parse_args()

    settings = get_settings()

    # 1. Create the client: same OpenAI SDK, pointed at Gemini's server.
    client = OpenAI(
        api_key=settings.llm_api_key.get_secret_value(),
        base_url=settings.llm_base_url,
    )

    # 2. Build the messages: the system prompt sets behaviour, the user message asks.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": args.question},
    ]

    # Only send temperature if the user asked for one; otherwise use the model default.
    extra_options = {}
    if args.temperature is not None:
        extra_options["temperature"] = args.temperature

    # 3. Send the request (this is "inference": the model generating an answer).
    try:
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            **extra_options,
        )
    except openai.AuthenticationError:
        print("ERROR: API key rejected. Check LLM_API_KEY in .env")
        return
    except openai.NotFoundError:
        print(f"ERROR: Model '{settings.llm_model}' not found. Check LLM_MODEL in .env")
        return
    except openai.RateLimitError as error:
        print("ERROR: Rate limit / quota exceeded (HTTP 429). Wait a minute or try another model.")
        print(error)
        return
    except openai.APIConnectionError:
        print("ERROR: Could not reach the server. Check your internet connection.")
        return

    # 4. Read the answer and the token usage.
    answer = response.choices[0].message.content
    usage = response.usage

    print(f"Model:       {response.model}")
    print(f"Temperature: {args.temperature if args.temperature is not None else 'model default'}")
    print("-" * 60)
    print(answer)
    print("-" * 60)
    if usage:
        print(f"Input tokens:  {usage.prompt_tokens}")
        print(f"Output tokens: {usage.completion_tokens}  (the visible answer)")
        hidden = usage.total_tokens - usage.prompt_tokens - usage.completion_tokens
        print(f"Hidden tokens: {hidden}  (the model's internal 'thinking')")
        print(f"Total tokens:  {usage.total_tokens}")


if __name__ == "__main__":
    main()
