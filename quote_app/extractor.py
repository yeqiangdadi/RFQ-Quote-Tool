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


def _cluster_1d(values, tol):
    """Cluster sorted numeric values; return list of lists."""
    if not values:
        return []
    clusters = [[values[0]]]
    for v in values[1:]:
        if v - clusters[-1][-1] <= tol:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return clusters


def detect_lineless_tables(boxes, texts, shape, min_texts_per_row=2, col_gap_ratio=0.3):
    """Detect tables defined by text alignment (no cell borders).

    Strategy: find header row, then use NO column to identify row starters.
    """
    if len(boxes) < 4:
        return []

    h, w = shape[:2]

    # Filter tiny text
    filtered = []
    for box, text in zip(boxes, texts):
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        if bw < 8 or bh < 8 or bw * bh < 100:
            continue
        if not text or not text.strip():
            continue
        filtered.append((x0, y0, x1, y1, text))

    if len(filtered) < 4:
        return []

    # Find candidate header rows
    y_groups = {}
    for x0, y0, x1, y1, text in filtered:
        yc = round((y0 + y1) / 2)
        y_groups.setdefault(yc, []).append((x0, y0, x1, y1, text))

    sorted_yc = sorted(y_groups.keys())
    merged_groups = []
    current_group = [sorted_yc[0]]
    for yc in sorted_yc[1:]:
        if yc - current_group[-1] <= 15:
            current_group.append(yc)
        else:
            merged_groups.append(current_group)
            current_group = [yc]
    merged_groups.append(current_group)

    # Find header
    header_row = None
    for group in merged_groups:
        all_texts = []
        for yc in group:
            all_texts.extend(y_groups[yc])
        if len(all_texts) < 3:
            continue
        matched = sum(1 for _, _, _, _, t in all_texts if match_field(t))
        if matched >= 3:
            header_row = all_texts
            break

    if not header_row:
        return []

    header_row.sort(key=lambda r: r[0])
    med_w = int(np.median([x1 - x0 for x0, _, x1, _, _ in header_row]))
    header_y = max(y1 for _, _, _, y1, _ in header_row)

    # Detect column boundaries from data x-distribution in BOM region only
    # BOM region: x from header's x-range, y from header to ~400px below
    header_x0 = min(x0 for x0, _, _, _, _ in header_row)
    header_x1 = max(x1 for _, _, _, x1, _ in header_row)
    bom_texts = [(x0, y0, x1, y1, t) for x0, y0, x1, y1, t in filtered
                 if y0 > header_y + 10 and y0 < header_y + 400 and x0 >= header_x0 - 20]
    data_x_starts = sorted(set(x0 for x0, _, _, _, _ in bom_texts))
    x_col_clusters = _cluster_1d(data_x_starts, 50)  # larger tolerance to merge nearby starts
    data_col_centers = [int(np.mean(c)) for c in x_col_clusters if len(c) >= 3]

    if len(data_col_centers) >= 3:
        col_centers = data_col_centers
    else:
        col_centers = [(x0 + x1) / 2 for x0, _, x1, _, _ in header_row]

    # Find row starters: texts in the first column (NO column) that look like row numbers
    no_col_x = col_centers[0]
    no_col_tol = med_w // 2
    row_starters = []
    for x0, y0, x1, y1, text in filtered:
        xc = (x0 + x1) / 2
        if abs(xc - no_col_x) <= no_col_tol and y0 > header_y + 10:
            # Check if text looks like a row number (single digit or small number)
            if re.match(r'^\d{1,2}$', text.strip()):
                row_starters.append((y0, text))

    row_starters.sort()
    if not row_starters:
        return []

    # Build rows from starters
    data_rows = []
    for i, (starter_y, _) in enumerate(row_starters):
        # Find all texts that belong to this row (within 60px below starter)
        if i + 1 < len(row_starters):
            row_end = row_starters[i + 1][0]
        else:
            row_end = starter_y + 100
        row_texts = [(x0, y0, x1, y1, t) for x0, y0, x1, y1, t in filtered
                     if starter_y - 5 <= y0 < row_end]
        if len(row_texts) >= min_texts_per_row:
            row_texts.sort(key=lambda r: r[0])
            data_rows.append(row_texts)

    if not data_rows:
        return []

    # Build cells
    cells = []

    # Header cells
    for x0, y0, x1, y1, text in header_row:
        cells.append({
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "w": x1 - x0, "h": y1 - y0,
            "_texts": [text],
        })

    # Data row cells
    for row in data_rows:
        row_ys = [y0 for _, y0, _, _, _ in row] + [y1 for _, _, _, y1, _ in row]
        ry0 = min(row_ys)
        ry1 = max(row_ys)

        # Assign each text to column based on x-start position (not center)
        col_starts = [c["x0"] for c in cells if c["y0"] == min(c["y0"] for c in cells)]  # header row x-starts
        # Actually use col_centers as boundaries: text belongs to column i if its x0 is between col_centers[i-1] and col_centers[i]
        col_boundaries = [0] + [(col_centers[i] + col_centers[i+1]) / 2 for i in range(len(col_centers)-1)] + [w]

        col_texts = {ci: [] for ci in range(len(col_centers))}
        for x0, y0, x1, y1, text in row:
            # Find which column this text belongs to based on x0
            ci = 0
            for bi in range(len(col_boundaries)-1):
                if col_boundaries[bi] <= x0 < col_boundaries[bi+1]:
                    ci = bi
                    break
            col_texts[ci].append((x0, y0, x1, y1, text))

        for ci in range(len(col_centers)):
            blocks = col_texts[ci]
            if not blocks:
                cx = col_centers[ci]
                cells.append({
                    "x0": cx - med_w // 2, "y0": ry0, "x1": cx + med_w // 2, "y1": ry1,
                    "w": med_w, "h": ry1 - ry0, "_texts": [],
                })
            else:
                cx0 = min(b[0] for b in blocks)
                cy0 = min(b[1] for b in blocks)
                cx1 = max(b[2] for b in blocks)
                cy1 = max(b[3] for b in blocks)
                cells.append({
                    "x0": cx0, "y0": cy0, "x1": cx1, "y1": cy1,
                    "w": cx1 - cx0, "h": cy1 - cy0,
                    "_texts": [b[4] for b in blocks],
                })

    if not cells:
        return []

    x0 = min(c["x0"] for c in cells)
    y0 = min(c["y0"] for c in cells)
    x1 = max(c["x1"] for c in cells)
    y1 = max(c["y1"] for c in cells)

    table_area = (x1 - x0) * (y1 - y0)
    page_area = h * w
    if table_area < page_area * 0.01 or table_area > page_area * 0.5:
        return []

    return [{
        "cells": cells,
        "bbox": (x0, y0, x1, y1),
        "rows": 1 + len(data_rows),
        "cols": len(col_centers),
    }]


def extract_with_columns(boxes, texts, col_positions, header_y_range=None):
    """Extract table using manually specified column positions.

    Args:
        boxes: OCR text boxes [(x0,y0,x1,y1), ...]
        texts: OCR texts [str, ...]
        col_positions: list of x-coordinates marking column centers/boundaries
        header_y_range: optional (y_min, y_max) to restrict header search

    Returns:
        List of tables in same format as extract()
    """
    if len(boxes) < 4 or len(col_positions) < 2:
        return []

    # Filter tiny text
    filtered = []
    for box, text in zip(boxes, texts):
        x0, y0, x1, y1 = box
        bw, bh = x1 - x0, y1 - y0
        if bw < 8 or bh < 8 or bw * bh < 100:
            continue
        if not text or not text.strip():
            continue
        filtered.append((x0, y0, x1, y1, text))

    if len(filtered) < 4:
        return []

    # Find header row
    y_groups = {}
    for x0, y0, x1, y1, text in filtered:
        yc = round((y0 + y1) / 2)
        y_groups.setdefault(yc, []).append((x0, y0, x1, y1, text))

    sorted_yc = sorted(y_groups.keys())
    merged_groups = []
    current_group = [sorted_yc[0]]
    for yc in sorted_yc[1:]:
        if yc - current_group[-1] <= 15:
            current_group.append(yc)
        else:
            merged_groups.append(current_group)
            current_group = [yc]
    merged_groups.append(current_group)

    header_row = None
    for group in merged_groups:
        if header_y_range:
            group_y = (min(group) + max(group)) / 2
            if group_y < header_y_range[0] or group_y > header_y_range[1]:
                continue
        all_texts = []
        for yc in group:
            all_texts.extend(y_groups[yc])
        if len(all_texts) < 2:
            continue
        matched = sum(1 for _, _, _, _, t in all_texts if match_field(t))
        if matched >= 2:
            header_row = all_texts
            break

    if not header_row:
        # If no header found, use first group with enough texts
        for group in merged_groups:
            if header_y_range:
                group_y = (min(group) + max(group)) / 2
                if group_y < header_y_range[0] or group_y > header_y_range[1]:
                    continue
            all_texts = []
            for yc in group:
                all_texts.extend(y_groups[yc])
            if len(all_texts) >= len(col_positions):
                header_row = all_texts
                break

    if not header_row:
        return []

    header_row.sort(key=lambda r: r[0])
    header_y = max(y1 for _, _, _, y1, _ in header_row)

    # Use header text box centers as column positions (more accurate than user markers)
    # User markers only determine the NUMBER of columns
    num_cols = len(col_positions)
    header_centers = sorted([(x0 + x1) / 2 for x0, y0, x1, y1, _ in header_row])

    # If header has enough boxes, use them; otherwise fall back to markers
    if len(header_centers) >= num_cols:
        # Take the first num_cols header centers, or distribute evenly
        if len(header_centers) == num_cols:
            col_positions = header_centers
        else:
            # Pick num_cols evenly spaced centers from header
            step = len(header_centers) / num_cols
            col_positions = [header_centers[int(i * step)] for i in range(num_cols)]
    # else: keep user's col_positions as-is

    # Sort column positions
    col_positions = sorted(col_positions)

    # Find data rows below header
    row_starters = []
    no_col_x = col_positions[0]
    no_col_tol = 30
    for x0, y0, x1, y1, text in filtered:
        xc = (x0 + x1) / 2
        if abs(xc - no_col_x) <= no_col_tol and y0 > header_y + 10:
            if re.match(r'^\d{1,3}$', text.strip()):
                row_starters.append((y0, text))

    row_starters.sort()
    data_rows = []
    # Restrict to BOM x-range (from first column position to last column + some margin)
    bom_x_min = col_positions[0] - 50
    bom_x_max = col_positions[-1] + 200  # last column + margin for wide text
    for i, (starter_y, _) in enumerate(row_starters):
        if i + 1 < len(row_starters):
            row_end = row_starters[i + 1][0]
        else:
            row_end = starter_y + 100
        row_texts = [(x0, y0, x1, y1, t) for x0, y0, x1, y1, t in filtered
                     if starter_y - 5 <= y0 < row_end and bom_x_min <= x0 <= bom_x_max]
        if row_texts:
            row_texts.sort(key=lambda r: r[0])
            data_rows.append(row_texts)

    if not data_rows:
        return []

    # Build cells using given column positions as boundaries
    cells = []

    # Header cells
    for x0, y0, x1, y1, text in header_row:
        cells.append({
            "x0": x0, "y0": y0, "x1": x1, "y1": y1,
            "w": x1 - x0, "h": y1 - y0,
            "_texts": [text],
        })

    # Data row cells - use marker-based grouping with nearest-neighbor assignment
    num_cols = len(col_positions)
    for row in data_rows:
        row_ys = [y0 for _, y0, _, _, _ in row] + [y1 for _, _, _, y1, _ in row]
        ry0 = min(row_ys)
        ry1 = max(row_ys)

        # Sort text boxes by x position
        sorted_row = sorted(row, key=lambda b: b[0])

        # Calculate midpoints between consecutive markers as boundaries
        boundaries = []
        for i in range(len(col_positions) - 1):
            mid = (col_positions[i] + col_positions[i + 1]) / 2
            boundaries.append(mid)
        boundaries = [0] + boundaries + [99999]

        # Assign each text box to column based on its center position
        col_groups = {ci: [] for ci in range(num_cols)}
        for x0, y0, x1, y1, text in sorted_row:
            xc = (x0 + x1) / 2
            ci = 0
            for bi in range(len(boundaries) - 1):
                if boundaries[bi] <= xc < boundaries[bi + 1]:
                    ci = bi
                    break
            col_groups[ci].append((x0, y0, x1, y1, text))

        # Create cells for each column
        for ci in range(num_cols):
            blocks = col_groups[ci]
            if not blocks:
                cx = col_positions[ci]
                cells.append({
                    "x0": cx - 20, "y0": ry0, "x1": cx + 20, "y1": ry1,
                    "w": 40, "h": ry1 - ry0, "_texts": [],
                })
            else:
                cx0 = min(b[0] for b in blocks)
                cy0 = min(b[1] for b in blocks)
                cx1 = max(b[2] for b in blocks)
                cy1 = max(b[3] for b in blocks)
                cells.append({
                    "x0": cx0, "y0": cy0, "x1": cx1, "y1": cy1,
                    "w": cx1 - cx0, "h": cy1 - cy0,
                    "_texts": [b[4] for b in blocks],
                })

    if not cells:
        return []

    # Build table structure
    cell_text_map = {i: c.get("_texts", []) for i, c in enumerate(cells)}

    # Group cells by row
    by_row = {}
    for i, c in enumerate(cells):
        key = round(c["y0"] / 4)
        by_row.setdefault(key, []).append((c["x0"], i))

    rows = []
    for key in sorted(by_row):
        items = sorted(by_row[key])
        rows.append([(x, cell_text_map[i]) for x, i in items])

    if not rows:
        return []

    # Find header row index
    header = pick_header(rows)
    if not header:
        header_idx = 0
        headers = [(x, None, " ".join(parts)) for x, parts in rows[0]]
    else:
        header_idx, headers = header

    records = rows_to_records(rows, header_idx, headers)
    if not records:
        return []

    source_headers = [text for _, _, text in headers]
    return [{
        "bbox": (min(c["x0"] for c in cells), min(c["y0"] for c in cells),
                 max(c["x1"] for c in cells), max(c["y1"] for c in cells)),
        "header": source_headers,
        "records": records,
        "items": to_quote_items(records),
    }]


def extract(rgb, boxes, texts):
    results = []

    # Path 1: bordered tables (existing)
    cells = detect_cells(rgb)
    tables = group_tables(cells)
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

    # Path 2: lineless tables (new)
    lineless_tables = detect_lineless_tables(boxes, texts, rgb.shape)
    for t in lineless_tables:
        # Reuse assign_text with the synthetic cells
        cell_text_map = {i: c.get("_texts", []) for i, c in enumerate(t["cells"])}
        rows = build_table_rows(t, cell_text_map)
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
