"""Offline PaddleOCR wrapper used by the quotation app."""

import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "offline" / "paddlex_cache"

os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(CACHE_DIR))
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

RENDER_SCALE = float(os.environ.get("QUOTE_OCR_SCALE", "2.5"))

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    global _engine
    if _engine is None:
        from paddleocr import PaddleOCR

        kwargs = dict(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        if sys.platform == "win32":
            # paddle 3.3 onednn hits Unimplemented Attribute on some Windows
            # CPUs; plain CPU kernels are correct and fast enough here.
            os.environ.setdefault("FLAGS_use_mkldnn", "0")
            kwargs["enable_mkldnn"] = False
        _engine = PaddleOCR(**kwargs)
    return _engine


def is_ready():
    return _engine is not None


def warmup():
    get_engine()


def render_pages(path, preview_width=1400):
    """Yield (page_no, PIL image, preview PIL image)."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        pdf = pdfium.PdfDocument(str(path))
        for index, page in enumerate(pdf):
            image = page.render(scale=RENDER_SCALE).to_pil().convert("RGB")
            yield index + 1, image, _preview(image, preview_width)
    else:
        image = Image.open(path).convert("RGB")
        yield 1, image, _preview(image, preview_width)


def _preview(image, width):
    if image.width <= width:
        return image.copy()
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.LANCZOS)


def ocr_image(image):
    """Run OCR on a PIL image; returns (boxes, texts)."""
    array = np.array(image)
    with _engine_lock:
        results = get_engine().predict(array)
        boxes, texts = [], []
        for result in results:
            boxes.extend([[int(v) for v in box] for box in result["rec_boxes"]])
            texts.extend([str(t) for t in result["rec_texts"]])
    return boxes, texts
