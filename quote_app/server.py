"""Local web app: upload a drawing, edit the extracted RFQ, export Excel / print PDF."""

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import exporter

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / "static"
OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="图纸询价单生成器")
app.mount("/media", StaticFiles(directory=str(OUTPUT)), name="media")

JOBS = {}
OCR_LOCK = threading.Lock()
JOB_TTL = 12 * 3600


class ExportRequest(BaseModel):
    filename: str = "报价单"
    items: list[dict] = []


def _cleanup_jobs():
    now = time.time()
    for job_id, job in list(JOBS.items()):
        if now - job["created"] > JOB_TTL:
            JOBS.pop(job_id, None)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/print")
def print_page():
    return FileResponse(STATIC / "print.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    _cleanup_jobs()
    suffix = Path(file.filename or "drawing.pdf").suffix.lower() or ".pdf"
    if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}:
        raise HTTPException(400, "仅支持 PDF 或常见图片格式")

    job_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    workdir = OUTPUT / job_id
    workdir.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r'[\\/:*?"<>|]+', "-", Path(file.filename or "drawing").stem).strip() or "drawing"
    source = workdir / f"{stem[:80]}{suffix}"
    with source.open("wb") as handle:
        while chunk := await file.read(1 << 20):
            handle.write(chunk)

    job = {
        "id": job_id,
        "source": file.filename,
        "status": "queued",
        "stage": "排队中",
        "percent": 0,
        "result": None,
        "error": None,
        "created": time.time(),
    }
    JOBS[job_id] = job

    def run():
        with OCR_LOCK:
            job["status"] = "running"
            cmd = [sys.executable, "-m", "quote_app.worker", str(source), str(workdir)]
            proc = subprocess.Popen(cmd, cwd=str(ROOT))
            while proc.poll() is None:
                _read_progress(job, workdir)
                time.sleep(0.5)
            _read_progress(job, workdir)
            result_path = workdir / "result.json"
            if proc.returncode == 0 and result_path.exists():
                job["result"] = json.loads(result_path.read_text(encoding="utf-8"))
                job["status"] = "done"
            else:
                error_path = workdir / "error.txt"
                job["error"] = (
                    error_path.read_text(encoding="utf-8")
                    if error_path.exists()
                    else f"识别进程异常退出（代码 {proc.returncode}）"
                )
                job["status"] = "error"

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": job_id, "source": file.filename}


def _read_progress(job, workdir):
    try:
        data = json.loads((workdir / "progress.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if data.get("stage"):
        job["stage"] = data["stage"]
    job["percent"] = int(data.get("percent") or 0)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "任务不存在或已过期")
    payload = {k: job[k] for k in ("id", "source", "status", "stage", "percent", "error")}
    payload["job_id"] = job["id"]
    payload["workdir"] = job_id
    payload["elapsed"] = int(time.time() - job["created"])
    if job["status"] == "done" and job["result"]:
        payload.update(job["result"])
    return payload


@app.post("/api/export")
def export(request: ExportRequest):
    filename = (request.filename or "报价单").strip().replace("/", "-")
    if not filename.lower().endswith(".xlsx"):
        filename += ".xlsx"
    target = OUTPUT / "exports" / filename
    exporter.export_quote(request.items, target)
    data = target.read_bytes()
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


def _free_port(start=8765):
    import socket

    for port in range(start, start + 20):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    return start


def main():
    import uvicorn

    port = int(os.environ.get("QUOTE_PORT", "0")) or _free_port()
    url = f"http://127.0.0.1:{port}"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"\n  图纸询价单生成器已启动：{url}\n  关闭此窗口即停止服务。\n")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
