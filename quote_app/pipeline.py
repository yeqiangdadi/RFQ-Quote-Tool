"""Drawing -> quotation items pipeline."""

import time
from pathlib import Path

import numpy as np

from . import extractor, ocr_engine

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"


def _notify(progress, stage, percent):
    if progress:
        progress(stage, percent)


def analyze(path, workdir, progress=None):
    path = Path(path)
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    _notify(progress, "解析图纸", 10)
    page_items = list(ocr_engine.render_pages(path))
    total_pages = len(page_items)

    pages = []
    tables = []
    for index, (page_no, image, preview) in enumerate(page_items, 1):
        _notify(progress, f"识别第 {index}/{total_pages} 页", 10 + int(80 * (index - 1) / total_pages))
        preview_name = f"page{page_no}.jpg"
        preview.save(workdir / preview_name, quality=82)

        boxes, texts = ocr_engine.ocr_image(image)
        found = extractor.extract(np.array(image), boxes, texts)

        scale = preview.width / image.width
        for table in found:
            x0, y0, x1, y1 = table["bbox"]
            table["bbox"] = [round(x0 * scale), round(y0 * scale), round(x1 * scale), round(y1 * scale)]
            table["page"] = page_no
        pages.append(
            {
                "page": page_no,
                "preview": preview_name,
                "width": preview.width,
                "height": preview.height,
                "ocr_lines": len(texts),
                "tables": [
                    {"bbox": t["bbox"], "header": t["header"], "count": len(t["records"])}
                    for t in found
                ],
            }
        )
        tables.extend(found)
        _notify(progress, f"识别第 {index}/{total_pages} 页", 10 + int(80 * index / total_pages))

    _notify(progress, "整理报价条目", 92)
    groups = {}
    for table in tables:
        groups.setdefault(tuple(table["header"]), []).append(table)
    primary = max(groups.values(), key=lambda g: sum(len(t["records"]) for t in g), default=[])

    items = []
    for table in sorted(primary, key=lambda t: t["page"]):
        items.extend(table["items"])

    source_headers = list(primary[0]["header"]) if primary else []
    notes = []
    if not items:
        notes.append("未识别到带表头的材料表，请检查图纸清晰度或手动添加行。")
    if len(groups) > 1:
        others = sum(len(t["records"]) for g in groups.values() if g is not primary for t in g)
        notes.append(f"图纸中有 {len(groups)} 组不同表头的表格，已选用条目最多的一组；其余 {others} 条未导入。")
    if total_pages > 1:
        notes.append(f"共识别 {total_pages} 页，材料表条目已按页序合并。")

    _notify(progress, "完成", 100)
    return {
        "source": path.name,
        "stem": path.stem,
        "pages": pages,
        "items": items,
        "source_headers": source_headers,
        "notes": notes,
    }
