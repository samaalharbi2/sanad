"""خادم موقع سَنَد.

التشغيل:  python -m sanad.web.server
ثم افتح:  http://localhost:8000
"""
import json
import tempfile
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sanad.pii.detector import UnreadableFile, scan_path
from sanad.web.recommend import finding_action, recommendations

STATIC = Path(__file__).parent / "static"
ALLOWED = {".csv", ".xlsx", ".jsonl", ".txt", ".docx", ".pdf"}
MAX_BYTES = 50 * 1024 * 1024
MAX_FILES = 10
UNAVAILABLE = "المساعد غير متاح حاليًا. تأكد أن Ollama يعمل ثم حاول مرة ثانية."

app = FastAPI(title="Sanad")


@app.exception_handler(RequestValidationError)
async def bad_request(request, exc):  # أي طلب ناقص: رسالة عربية واضحة بدل تفاصيل تقنية
    return JSONResponse({"detail": "الطلب غير مكتمل. حدّث الصفحة (Ctrl+F5) وحاول مرة ثانية."}, status_code=400)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
SCANS = {}  # نتائج الفحص في الذاكرة فقط، ولا تُحفظ على القرص


def source_list(hits):
    return [{"doc": h["meta"]["doc_title"], "article": h["meta"]["article"],
             "amended": h["meta"]["status"] == "amended"} for h in hits]


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    """حالة النظام الفعلية: الفحص متاح دائمًا، والمساعد والأسماء تحتاج النموذج المحلي."""
    from sanad.pipeline.incremental import model_ready
    return {"scan": True, "model": model_ready(), "max_files": MAX_FILES,
            "max_mb": MAX_BYTES // (1024 * 1024), "formats": sorted(ALLOWED)}


@app.get("/report")
def report_page():
    return FileResponse(STATIC / "report.html")


@app.post("/api/scan")
async def scan(files: list[UploadFile] = File(None), file: UploadFile = File(None)):
    files = list(files or []) + ([file] if file else [])  # يقبل ملفًا واحدًا أو عدة ملفات
    if not files:
        raise HTTPException(400, "اختر ملفًا واحدًا على الأقل.")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"الحد الأقصى {MAX_FILES} ملفات في المرة الواحدة.")
    results, findings = [], []
    with tempfile.TemporaryDirectory() as d:  # الملفات تُحذف فور انتهاء الفحص
        for i, up in enumerate(files):
            name = up.filename or f"ملف {i + 1}"
            entry = {"name": name, "error": ""}
            suffix = Path(name).suffix.lower()
            data = await up.read()
            if suffix not in ALLOWED:
                entry["error"] = "صيغة غير مدعومة"
            elif len(data) > MAX_BYTES:
                entry["error"] = "أكبر من 50 ميجابايت"
            else:
                p = Path(d) / f"upload_{i}{suffix}"
                p.write_bytes(data)
                try:
                    stats, found = scan_path(p, use_llm=True, display_name=name)
                    entry.update(stats, found=len(found))
                    findings += found
                except UnreadableFile as e:
                    entry["error"] = str(e)
                except Exception:
                    entry["error"] = "تعذّرت قراءته"
            results.append(entry)

    for f in findings:
        f["action"] = finding_action(f)
    ok = [r for r in results if not r["error"]]
    if not ok:
        raise HTTPException(400, results[0]["error"] if len(results) == 1 else "تعذّرت قراءة الملفات. الصيغ المدعومة: إكسل وCSV وWord وPDF والنص.")
    scan_id = uuid.uuid4().hex
    names = [r["name"] for r in ok]
    result = {
        "scan_id": scan_id,
        "files": results,
        "records": sum(r["records"] for r in ok),
        "findings": findings,
        "recommendations": recommendations(findings, names),
    }
    SCANS[scan_id] = {"files": names, "findings": findings, "result": result, "at": datetime.now(),
                      "structure": [r for r in results if not r["error"]]}
    return result


class Question(BaseModel):
    question: str
    scan_id: str


@app.post("/api/ask")
def ask(q: Question):
    """يبث الإجابة سطرًا سطرًا (NDJSON): أجزاء النص أول بأول، وآخر سطر المصادر اللي ذكرتها الإجابة."""
    from sanad.assistant import stream_about_file
    if not q.question.strip():
        raise HTTPException(400, "اكتب سؤالك أولًا.")
    scan_ = SCANS.get(q.scan_id)
    if not scan_:
        raise HTTPException(404, "انتهت صلاحية الفحص. ارفع الملفات مرة ثانية.")
    try:
        hits, gen = stream_about_file(q.question, scan_["findings"], scan_["files"],
                                      structure=scan_.get("structure"),
                                      recs=scan_["result"]["recommendations"])
    except Exception:
        raise HTTPException(503, UNAVAILABLE)

    def lines():
        from sanad.assistant import cited_sources, dedupe_sources, ref_hits
        text = ""
        try:
            for piece in gen:
                text += piece
                yield json.dumps({"t": piece}, ensure_ascii=False) + "\n"
        except Exception:
            yield json.dumps({"error": UNAVAILABLE}, ensure_ascii=False) + "\n"
        # المصادر في الآخر: فقط المواد اللي الإجابة ذكرتها فعلًا
        known = hits + ref_hits(scan_["result"]["recommendations"])
        yield json.dumps({"sources": source_list(dedupe_sources(cited_sources(text, known)))}, ensure_ascii=False) + "\n"

    return StreamingResponse(lines(), media_type="application/x-ndjson")


# ---------- المراقبة الدورية ----------
STALE_DAYS = 365


def _latest(folder):
    """آخر فحص للمجلد + وش تغيّر عن الفحص اللي قبله."""
    from sanad.pipeline import warehouse as wh
    runs = wh.runs(folder)
    if not runs:
        return runs, None
    meta, files, findings = wh.run_detail(runs[-1]["run_id"])
    for f in findings:
        f["action"] = finding_action(f)
    with_pii = {f["file"] for f in findings}
    prev = set()
    if len(runs) > 1:
        prev = {f["file"] for f in wh.run_detail(runs[-2]["run_id"])[2]}
    old = datetime.now() - timedelta(days=STALE_DAYS)
    stale = sorted({f["file"] for f in findings if f["modified_at"] and f["modified_at"] < old})
    latest = {
        "run": meta, "files": files, "findings": findings,
        "changes": {"new": sorted(with_pii - prev) if len(runs) > 1 else [],
                    "resolved": sorted(prev - with_pii)},
        "stale": stale,
        "recommendations": recommendations(findings, [f["name"] for f in files], stale),
    }
    return runs, latest


@app.get("/api/monitor")
def monitor():
    from sanad.pipeline import warehouse as wh
    from sanad.pipeline.incremental import STATUS
    folder = wh.get_folder()
    out = {"folder": folder, "exists": bool(folder) and Path(folder).is_dir(), "status": STATUS,
           "runs": [], "latest": None}
    if out["exists"]:
        out["runs"], out["latest"] = _latest(str(Path(folder).resolve()))
    return out


class Folder(BaseModel):
    folder: str


@app.post("/api/monitor/folder")
def monitor_folder(f: Folder):
    from sanad.pipeline import warehouse as wh
    folder = f.folder.strip().strip('"')
    if not folder or not Path(folder).is_dir():
        raise HTTPException(400, "المجلد غير موجود. انسخ مساره كامل من مستكشف الملفات.")
    wh.set_folder(str(Path(folder).resolve()))
    return {"ok": True}


@app.post("/api/monitor/run")
def monitor_run():
    from sanad.pipeline import warehouse as wh
    from sanad.pipeline.incremental import STATUS, run_scan
    folder = wh.get_folder()
    if not folder or not Path(folder).is_dir():
        raise HTTPException(400, "حدد المجلد أولًا.")
    if STATUS["running"]:
        raise HTTPException(409, "فيه فحص شغّال الحين.")
    STATUS.update(running=True, done=0, total=0, current="", error="")

    def work():
        try:
            run_scan(folder, use_llm=True, trigger="manual", log=lambda m: None)
        except Exception as e:  # noqa: BLE001
            STATUS.update(running=False, error=str(e))
    threading.Thread(target=work, daemon=True).start()
    return {"started": True}


# ---------- التقرير ----------
@app.get("/api/report")
def report_data(scan: str = "", run: str = ""):
    if scan:
        s_ = SCANS.get(scan)
        if not s_:
            raise HTTPException(404, "انتهت صلاحية الفحص. ارفع الملفات مرة ثانية.")
        r = s_["result"]
        return {"kind": "scan", "generated_at": datetime.now(), "scanned_at": s_["at"], "folder": "",
                "files": r["files"], "records": r["records"], "findings": r["findings"],
                "recommendations": r["recommendations"]}
    from sanad.pipeline import warehouse as wh
    folder = wh.get_folder()
    runs, latest = _latest(str(Path(folder).resolve())) if folder and Path(folder).is_dir() else ([], None)
    if not latest:
        raise HTTPException(404, "ما فيه فحص دوري محفوظ بعد.")
    files = [{"name": f["name"], "error": f["error"] or "", "records": f["records"] or 0, "found": f["found"]}
             for f in latest["files"]]
    return {"kind": "run", "generated_at": datetime.now(), "scanned_at": latest["run"]["finished_at"],
            "folder": folder, "files": files, "records": sum(f["records"] for f in files),
            "findings": latest["findings"], "recommendations": latest["recommendations"]}


def _warmup():
    try:
        from sanad.assistant import warmup
        warmup()
        print("سَنَد جاهز للأسئلة.")
    except Exception:
        print("تنبيه: Ollama غير شغّال، الفحص يشتغل لكن الأسئلة لا.")


def main():
    import threading
    import uvicorn
    print("سَنَد يعمل على: http://localhost:8000")
    threading.Thread(target=_warmup, daemon=True).start()  # تحميل النموذج في الخلفية
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()