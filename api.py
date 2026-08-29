"""Business-logic layer over the Ollama model.

No web framework yet -- these are plain functions. A future FastAPI app
will add routes that call straight into generate_text() / chat().
"""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf as fitz
import pytesseract
from PIL import Image

from class_structure import Invoice, InvoiceHeader
from model import OllamaModel, DEFAULT_MODEL
from prompt import SYSTEM_PROMPT, build_user_prompt

_default_model = OllamaModel()

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MIN_NATIVE_TEXT_CHARS = 40  # below this, treat the PDF as scanned and OCR it instead
_HEADER_FIELDS = set(InvoiceHeader.model_fields)


def _resolve_model(model: str | None) -> OllamaModel:
    if model is None or model == DEFAULT_MODEL:
        return _default_model
    return OllamaModel(model=model)


def generate_text(prompt: str, model: str | None = None) -> str:
    return _resolve_model(model).generate(prompt)


def chat(messages: list[dict], model: str | None = None) -> str:
    return _resolve_model(model).chat(messages)


def stream_generate(prompt: str, model: str | None = None):
    yield from _resolve_model(model).stream_generate(prompt)


def stream_chat(messages: list[dict], model: str | None = None):
    yield from _resolve_model(model).stream_chat(messages)


def _pdf_native_text(path: Path) -> str | None:
    """Text layer of a born-digital PDF -- more accurate than OCR when present."""
    with fitz.open(path) as doc:
        text = "\n\n".join(page.get_text() for page in doc)
    return text if len(text.strip()) >= MIN_NATIVE_TEXT_CHARS else None


def _pdf_ocr_text(path: Path) -> str:
    """Scanned PDF: rasterize each page and OCR it."""
    texts = []
    with fitz.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            texts.append(pytesseract.image_to_string(image))
    return "\n\n".join(texts)


def _image_ocr_text(path: Path) -> str:
    return pytesseract.image_to_string(Image.open(path))


def _extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_native_text(path) or _pdf_ocr_text(path)
    if suffix in IMAGE_EXTENSIONS:
        return _image_ocr_text(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def _renest_header(raw: dict) -> dict:
    """The model sometimes flattens invoice_header's fields to the top level
    despite the nested schema -- lift them back under invoice_header."""
    if isinstance(raw.get("invoice_header"), dict):
        return raw
    header = {k: raw.pop(k) for k in list(raw.keys()) if k in _HEADER_FIELDS}
    raw["invoice_header"] = header
    return raw


def extract_invoice(path: Path, model: str | None = None) -> Invoice:
    text = _extract_text(path)
    raw = _resolve_model(model).extract_json(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt(path.name, text),
        schema=Invoice.model_json_schema(),
    )
    return Invoice.model_validate(_renest_header(raw))
