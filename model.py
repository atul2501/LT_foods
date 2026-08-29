"""Thin wrapper around a local Ollama model (Gemma 4)."""

from __future__ import annotations

import json
import os

import ollama
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemma4:31b"


def _build_client(host: str | None) -> ollama.Client:
    """Local Ollama by default; if OLLAMA_API_KEY is set, talk to Ollama Cloud instead."""
    host = host or os.environ.get("OLLAMA_HOST")
    api_key = os.environ.get("OLLAMA_API_KEY")
    kwargs: dict = {}
    if host:
        kwargs["host"] = host
    if api_key:
        kwargs["headers"] = {"Authorization": f"Bearer {api_key}"}
    return ollama.Client(**kwargs)


class OllamaModel:
    def __init__(self, model: str = DEFAULT_MODEL, host: str | None = None):
        self.model = model
        self.client = _build_client(host)

    def generate(self, prompt: str, **options) -> str:
        response = self.client.generate(model=self.model, prompt=prompt, options=options or None)
        return response["response"]

    def chat(self, messages: list[dict], **options) -> str:
        response = self.client.chat(model=self.model, messages=messages, options=options or None)
        return response["message"]["content"]

    def stream_generate(self, prompt: str, **options):
        for chunk in self.client.generate(model=self.model, prompt=prompt, options=options or None, stream=True):
            yield chunk["response"]

    def stream_chat(self, messages: list[dict], **options):
        for chunk in self.client.chat(model=self.model, messages=messages, options=options or None, stream=True):
            yield chunk["message"]["content"]

    def extract_json(self, system_prompt: str, user_prompt: str, schema: dict) -> dict:
        """Chat call constrained to return JSON matching `schema` (Ollama structured outputs)."""
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            format=schema,
        )
        return json.loads(response["message"]["content"])
