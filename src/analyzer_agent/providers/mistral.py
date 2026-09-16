import os

from mistralai.client import Mistral

from .base import LLMProvider


class MistralProvider(LLMProvider):
    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY is not set")
        self._client = Mistral(api_key=api_key)

    def generate_json(self, prompt: str) -> str:
        response = self._client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content