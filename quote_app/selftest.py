"""Check the installed OCR pipeline against the bundled sample drawing."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples"
WORKDIR = ROOT / "output" / "selftest"


def load_expected():
    return json.loads((SAMPLES / "expected.json").read_text(encoding="utf-8"))


def main():
    from quote_app import exporter, pipeline

    sample = SAMPLES / "00-A-0001-12-1CS3.pdf"
    if not sample.exists():
        print(f"[FAIL] sample drawing missing: {sample}")
        return 1

    expected = load_expected()
    expected_items = expected["items"]

    print(f"Drawing : {sample.name}")
    print(f"Expected: {len(expected_items)} items")
    print("Running OCR on one page, usually 1-3 minutes ...")

    started = time.time()
    shown = [0]

    def progress(stage, percent):
        if percent >= shown[0] + 20:
            print(f"  {percent:3d}%  {stage}")
            shown[0] = percent

    result = pipeline.analyze(sample, WORKDIR, progress=progress)
    items = result["items"]
    elapsed = time.time() - started

    actual_path = WORKDIR / "actual_quote.xlsx"
    exporter.export_quote(items, actual_path)

    print()
    print(f"Recognized {len(items)} items in {elapsed:.0f}s")
    desc_key = next((h for h in (result.get("source_headers") or []) if "desc" in h.lower()), None)
    print(f"{'#':>2}  {'description':<44}")
    for number, item in enumerate(items, 1):
        label = item["source"].get(desc_key, "") if desc_key else ""
        print(f"{number:>2}  {str(label)[:44]:<44}")

    problems = []
    if len(items) != len(expected_items):
        problems.append(f"row count {len(items)}, expected {len(expected_items)}")

    matched = 0
    for index, exp in enumerate(expected_items[: len(items)], 1):
        got = items[index - 1]
        got_desc = got["source"].get(desc_key, "") if desc_key else ""
        exp_desc = exp["source"].get(desc_key, "") if desc_key else ""
        if got_desc == exp_desc:
            matched += 1
        else:
            print(f"  differs at row {index}: expected {exp_desc} / got {got_desc}")

    empty = sum(1 for item in items if desc_key and not str(item["source"].get(desc_key, "")).strip())
    if empty:
        problems.append(f"{empty} rows without description")

    ratio = matched / max(len(expected_items), 1)
    print()
    print(f"Description matches: {matched}/{len(expected_items)} ({ratio:.0%})")
    print(f"Workbook written: {actual_path}")
    for line in problems:
        print(f"  problem: {line}")

    if problems or ratio < 0.8:
        print("SELF-TEST FAILED")
        return 1
    print("SELF-TEST PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
