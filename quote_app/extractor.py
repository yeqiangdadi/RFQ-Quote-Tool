import re

import cv2
import numpy as np

# (field, synonyms) — longest/most specific phrases first
FIELD_SYNONYMS = [
    ("row_number", ("row number", "row no", "item no", "item", "id", "序号", "项次", "行号")),
    ("code", ("item code", "material code", "code", "物料编码", "物料号", "编码", "代号")),
    ("description", ("item description", "description", "desc", "物料名称", "名称", "描述", "品名")),
    ("remarks", ("remarks", "remark", "备注", "说明")),
    ("uom", ("uom", "unit of measure", "unit", "计量单位", "单位")),
    ("quantity", ("quantity", "qty", "数量")),
    ("unit_weight", ("unit weight", "单重", "单位重量")),
    ("total_weight", ("total weight", "总重", "总重量")),
    ("unit_price", ("unit price", "单价")),
    ("total_price", ("total price", "amount", "总价", "金额")),
    ("spec", ("specification", "spec", "nominal size", "nd", "规格", "型号", "尺寸")),
]

FIELD_ORDER = [
    "row_number",
    "code",
    "description",
    "remarks",
    "uom",
    "quantity",
    "unit_weight",
    "total_weight",
    "unit_price",
    "total_price",
]


def _norm(text):
    return re.sub(r"[\s:：()\[\]_\-\/]+", " ", str(text)).strip().lower()


def match_field(text):
    t = _norm(text)
    if not t:
        return None
    for field, synonyms in FIELD_SYNONYMS:
        for syn in synonyms:
            s = _norm(syn)
            if t == s or t.startswith(s + " ") or t.endswith(" " + s):
                return field
    for field, synonyms in FIELD_SYNONYMS:
        for syn in synonyms:
            s = _norm(syn)
            if len(s) >= 3 and s in t:
                return field
    return None


class _DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def detect_cells(rgb, min_w=28, min_h=12, min_area=700):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (28, 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 28))
    horiz = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    vert = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
    grid = cv2.bitwise_or(horiz, vert)

    contours, hierarchy = cv2.findContours(grid, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return []
    page_area = rgb.shape[0] * rgb.shape[1]
    cells = []
    for i, cnt in enumerate(contours):
        if hierarchy[0][i][3] == -1:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        if w < min_w or h < min_h or w * h < min_area or w * h > page_area * 0.4:
            continue
        cx, cy = x + w / 2, y + h / 2
        if not (4 <= cx <= rgb.shape[1] - 4 and 4 <= cy <= rgb.shape[0] - 4):
            continue
        cells.append({"x0": x, "y0": y, "x1": x + w, "y1": y + h, "w": w, "h": h})
    return cells


def group_tables(cells, tol=6):
    n = len(cells)
    dsu = _DSU(n)

    def adjacent(a, b):
        h_overlap = min(a["y1"], b["y1"]) - max(a["y0"], b["y0"])
        v_overlap = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])
        if h_overlap > 0.4 * min(a["h"], b["h"]):
            gap = max(a["x0"], b["x0"]) - min(a["x1"], b["x1"])
            if -tol <= gap <= tol:
                return True
        if v_overlap > 0.4 * min(a["w"], b["w"]):
            gap = max(a["y0"], b["y0"]) - min(a["y1"], b["y1"])
            if -tol <= gap <= tol:
                return True
        return False

    for i in range(n):
        for j in range(i + 1, n):
            if adjacent(cells[i], cells[j]):
                dsu.union(i, j)

    groups = {}
    for i in range(n):
        groups.setdefault(dsu.find(i), []).append(cells[i])

    tables = []
    for group in groups.values():
        if len(group) < 4:
            continue
        heights = sorted(c["h"] for c in group)
        med_h = heights[len(heights) // 2]
        cut_gap = max(80, 3 * med_h)
        ys = sorted({c["y0"] for c in group})
        cuts = [ys[0]]
        prev = ys[0]
        for y in ys[1:]:
            if y - prev > cut_gap:
                cuts.append(y)
            prev = y
        segments = [[] for _ in range(len(cuts))]
        for c in group:
            idx = 0
            for k, cut in enumerate(cuts):
                if c["y0"] >= cut:
                    idx = k
            segments[idx].append(c)
        for cells_seg in segments:
            if len(cells_seg) < 4:
                continue
            ys = sorted({c["y0"] for c in cells_seg})
            row_bands = []
            for y in ys:
                if row_bands and y - row_bands[-1][-1] <= 4:
                    row_bands[-1].append(y)
                else:
                    row_bands.append([y])
            rows = len(row_bands)
            xs = sorted({c["x0"] for c in cells_seg})
            col_bands = []
            for x in xs:
                if col_bands and x - col_bands[-1][-1] <= 4:
                    col_bands[-1].append(x)
                else:
                    col_bands.append([x])
            if rows < 2 or len(col_bands) < 2:
                continue
            x0 = min(c["x0"] for c in cells_seg)
            y0 = min(c["y0"] for c in cells_seg)
            x1 = max(c["x1"] for c in cells_seg)
            y1 = max(c["y1"] for c in cells_seg)
            tables.append({"cells": cells_seg, "bbox": (x0, y0, x1, y1), "rows": rows, "cols": len(col_bands)})
    tables.sort(key=lambda t: (t["bbox"][1], t["bbox"][0]))
    return tables


def assign_text(cells, boxes, texts):
    """Return {cell_index: [texts sorted by reading order]} using max overlap."""
    out = {i: [] for i in range(len(cells))}
    for text, box in zip(texts, boxes):
        bx0, by0, bx1, by1 = box
        best, best_area = None, 0
        for i, c in enumerate(cells):
            ox = min(bx1, c["x1"]) - max(bx0, c["x0"])
            oy = min(by1, c["y1"]) - max(by0, c["y0"])
            if ox <= 0 or oy <= 0:
                continue
            area = ox * oy
            if area > best_area:
                best, best_area = i, area
        if best is not None:
            out[best].append((by0, bx0, text))
    for i in out:
        out[i].sort()
        out[i] = [t for _, _, t in out[i]]
    return out


def build_table_rows(table, cell_text):
    by_row = {}
    for i, c in enumerate(table["cells"]):
        key = round(c["y0"] / 4)
        by_row.setdefault(key, []).append((c["x0"], i))
    rows = []
    for key in sorted(by_row):
        items = sorted(by_row[key])
        rows.append([(x, cell_text[i]) for x, i in items])
    return rows


def map_header(row):
    """Return list of (x, field, header_text) for every non-empty header cell."""
    mapped = []
    for x, parts in row:
        text = " ".join(parts).strip()
        if text:
            mapped.append((x, match_field(text), text))
    return mapped


def pick_header(rows):
    best = (-1, None)
    for idx, row in enumerate(rows):
        mapped = map_header(row)
        fields = {f for _, f, _ in mapped if f}
        score = len(fields) + (2 if "quantity" in fields or "description" in fields else 0)
        if len(fields) >= 2 and score > best[0]:
            best = (score, (idx, mapped))
    return best[1]


def rows_to_records(rows, header_idx, headers):
    """Split data rows into per-column values.

    Returns a list of records; each record keeps the drawing's original
    header text and cell text verbatim (`source`) alongside the mapped
    fields used for header matching (`fields`).
    """
    records = []
    for row in rows[header_idx + 1 :]:
        source = {}
        fields = {}
        for x, parts in row:
            text = " ".join(parts).strip()
            if not text:
                continue
            best_i, best_dx = None, None
            for i, (hx, _, _) in enumerate(headers):
                dx = abs(x - hx)
                if best_dx is None or dx < best_dx:
                    best_i, best_dx = i, dx
            if best_i is None:
                continue
            _, field, header_text = headers[best_i]
            if field == "spec":
                text = normalize_size(text)
            if header_text in source:
                source[header_text] = (source[header_text] + " " + text).strip()
            else:
                source[header_text] = text
            if field:
                if field in fields:
                    fields[field] = (fields[field] + " " + text).strip()
                else:
                    fields[field] = text
        nonempty = sum(1 for v in source.values() if v)
        if nonempty >= 2 and any(fields.get(k) for k in ("description", "remarks", "quantity", "code")):
            records.append({"source": source, "fields": fields})
    return records


def normalize_size(text):
    """Repair common OCR glyphs around nominal sizes (3/4* -> 3/4", 12° -> 12")."""
    s = str(text or "").strip()
    s = s.replace("″", '"').replace("”", '"').replace("“", '"')
    s = s.replace("’", "'").replace("‘", "'").replace("´", "'")
    s = re.sub(r'(?<=[\d/])[*°º˙](?=[Xx×\s]|$)', '"', s)
    s = re.sub(r"\s*[Xx×]\s*", "X", s)
    if re.search(r'"X', s) and not s.endswith('"'):
        s += '"'
    m = re.fullmatch(r"(\d{1,2}(?:-\d+/\d+)?)", s)
    if m and float(m.group(1).split("-")[0]) <= 36:
        s += '"'
    return s.strip()


def to_quote_items(records):
    """Build quote items that keep the drawing's original columns verbatim.

    Every item carries `source` ({drawing header text: original cell text})
    plus the RFQ template fields (weights, prices).
    """
    items = []
    for rec in records:
        fields = rec["fields"]
        desc = (fields.get("description") or fields.get("remarks") or "").strip()
        if not desc:
            continue
        items.append(
            {
                "source": rec["source"],
                "unit_weight": "",
                "total_weight": "",
                "unit_price": "",
                "total_price": "",
            }
        )
    return items


def extract(rgb, boxes, texts):
    cells = detect_cells(rgb)
    tables = group_tables(cells)
    results = []
    for t in tables:
        cell_text = assign_text(t["cells"], boxes, texts)
        rows = build_table_rows(t, cell_text)
        header = pick_header(rows)
        if not header:
            continue
        header_idx, headers = header
        records = rows_to_records(rows, header_idx, headers)
        if records:
            source_headers = [text for _, _, text in headers]
            results.append(
                {
                    "bbox": t["bbox"],
                    "header": source_headers,
                    "records": records,
                    "items": to_quote_items(records),
                }
            )
    results.sort(key=lambda r: -len(r["records"]))
    return results
