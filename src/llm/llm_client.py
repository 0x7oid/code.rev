from google import genai
import os

_client = None


def ask_llm(prompt: str, model: str = "gemini-3.5-flash"):
    global _client
    if _client is None:
        api_key = os.environ.get("API_KEY")
        if not api_key:
            raise RuntimeError("API_KEY is not set.")
        _client = genai.Client(api_key=api_key)

    response = _client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text
