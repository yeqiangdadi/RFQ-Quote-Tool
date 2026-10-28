"""Run one OCR job in its own process so the web server stays responsive."""

import json
import sys
import time
import traceback
from pathlib import Path


def main():
    if len(sys.argv) < 3:
        print("usage: python -m quote_app.worker <source> <workdir>")
        return 2
    source = Path(sys.argv[1])
    workdir = Path(sys.argv[2])
    workdir.mkdir(parents=True, exist_ok=True)
    progress_file = workdir / "progress.json"

    def progress(stage, percent):
        payload = json.dumps({"stage": stage, "percent": percent, "at": time.time()}, ensure_ascii=False)
        progress_file.write_text(payload, encoding="utf-8")

    progress("载入 OCR 模型", 3)
    try:
        from . import pipeline

        result = pipeline.analyze(source, workdir, progress)
        (workdir / "result.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        progress("完成", 100)
    except Exception as exc:
        (workdir / "error.txt").write_text(f"{type(exc).__name__}: {exc}", encoding="utf-8")
        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
