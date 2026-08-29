"""Batch entry point: scan input/ for invoices (PDF or image) and write
extracted JSON to output/. Run with: python main.py

Also exposes a FastAPI app (health check + on-demand extraction). Run with:
    uvicorn main:app --reload
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from api import extract_invoice, IMAGE_EXTENSIONS
from class_structure import Invoice

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE = BASE_DIR / "process.log"

SUPPORTED_EXTENSIONS = {".pdf", *IMAGE_EXTENSIONS}

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

CONTENT_TYPE_EXTENSIONS = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
}

app = FastAPI(title="LT Foods Invoice Extraction API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract", response_model=Invoice)
async def extract(request: Request) -> Invoice:
    """Postman: Body > binary, pick the PDF/image file, send. Content-Type
    is set automatically by Postman from the file and used here to tell
    PDF from image."""
    content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    suffix = CONTENT_TYPE_EXTENSIONS.get(content_type)
    if suffix is None:
        raise HTTPException(status_code=415, detail=f"Unsupported content type: {content_type!r}")

    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Empty request body")

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(body)
        tmp.flush()
        try:
            return extract_invoice(Path(tmp.name))
        except Exception as exc:
            logging.exception("Extraction failed for uploaded %s file", suffix)
            raise HTTPException(status_code=422, detail=f"Extraction failed: {exc}") from exc


def main() -> None:
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    files = sorted(f for f in INPUT_DIR.iterdir() if f.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        logging.info("No invoices found in %s", INPUT_DIR)
        print("No invoices found in input/")
        return

    for path in files:
        try:
            invoice = extract_invoice(path)
            out_path = OUTPUT_DIR / f"{path.stem}.json"
            out_path.write_text(invoice.model_dump_json(indent=2))
            logging.info("Processed %s -> %s", path.name, out_path.name)
            print(f"OK   {path.name} -> {out_path.name}")
        except Exception as exc:
            logging.exception("Failed to process %s", path.name)
            print(f"FAIL {path.name}: {exc}")


if __name__ == "__main__":
    main()
