"""الفحص التزايدي: يمسح المجلد المراقب ويفحص فقط الملفات الجديدة أو اللي تغيّر محتواها.

كيف يعرف إن الملف تغيّر؟
  1) لو الحجم ووقت التعديل نفس آخر مرة ← نفس الملف، ما نقرأه أصلًا.
  2) غير كذا نحسب بصمة المحتوى (SHA-256). لو البصمة نفسها (مثلًا الملف انحفظ بدون تغيير) ← نتخطاه.
  3) غير كذا ← نفحصه ونحفظ اكتشافاته مربوطة ببصمته الجديدة.

التشغيل:  python -m sanad.pipeline.incremental "C:\\path\\to\\folder"
"""
import argparse
import hashlib
import threading
import time
from datetime import datetime
from pathlib import Path

from sanad.pii.detector import SUPPORTED, UnreadableFile, scan_path
from sanad.pipeline import warehouse as wh

SKIP_NAMES = {"ground_truth_columns.csv"}  # ملف الإجابات الصحيحة للتقييم، مو مصدر بيانات
_LOCK = threading.Lock()                    # فحص واحد في نفس الوقت
STATUS = {"running": False, "done": 0, "total": 0, "current": ""}


def fingerprint(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def list_files(folder: Path):
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and p.suffix.lower() in SUPPORTED
                  and p.name not in SKIP_NAMES and not p.name.startswith(("~$", ".")))


def _known_versions(folder):
    """آخر نسخة معروفة لكل ملف: {المسار: (file_id, البصمة, الحجم, وقت التعديل)} + كل البصمات المفحوصة."""
    with wh.connect() as con:
        latest = con.execute("""
            SELECT d.rel_path, d.file_id, v.fingerprint, v.size_bytes, v.modified_at
            FROM dim_file d JOIN file_version v USING (file_id)
            WHERE d.folder = ?
            QUALIFY ROW_NUMBER() OVER (PARTITION BY d.file_id ORDER BY v.scanned_at DESC) = 1""", (folder,)).fetchall()
        seen = set(con.execute("""SELECT v.file_id, v.fingerprint FROM file_version v
                                  JOIN dim_file d USING (file_id) WHERE d.folder = ?""", (folder,)).fetchall())
    return {r[0]: r[1:] for r in latest}, seen


def model_ready():
    """النموذج المحلي شغّال؟ (بدونه ما تنكشف الأسماء، والملف ما يرجع يُفحص لأنه ما تغيّر)."""
    try:
        import ollama
        from sanad.config import load_settings
        ollama.Client(host=load_settings()["ollama"]["host"]).list()
        return True
    except Exception:  # noqa: BLE001
        return False


def run_scan(folder, use_llm=True, trigger="manual", log=print):
    """يرجع ملخص الفحص. الكتابة في المستودع تصير مرة وحدة في النهاية (قفل قصير)."""
    root = Path(folder)
    if not root.is_dir():
        raise FileNotFoundError(f"المجلد غير موجود: {folder}")
    if use_llm and not model_ready():
        # نوقف بدل ما نحفظ نتائج ناقصة، وPrefect يعيد المحاولة بعد شوي
        raise RuntimeError("Ollama غير شغّال. شغّله ثم أعد الفحص.")
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError("فيه فحص شغّال الحين")
    try:
        wh.init()
        folder = str(root.resolve())
        started = datetime.now()
        known, seen = _known_versions(folder)
        files = list_files(root)
        STATUS.update(running=True, done=0, total=len(files), current="")
        plan = []  # (المسار، البصمة، الإجراء، الحجم، وقت التعديل، السجلات، الخطأ، الاكتشافات)
        for i, p in enumerate(files):
            rel = p.relative_to(root).as_posix()
            STATUS.update(done=i, current=rel)
            st = p.stat()
            mtime = datetime.fromtimestamp(st.st_mtime).replace(microsecond=0)
            prev = known.get(rel)
            if prev and prev[2] == st.st_size and prev[3] == mtime:
                plan.append((rel, prev[1], "skipped", None, None, None, None, None))
                continue
            fp = fingerprint(p)
            if prev and (prev[0], fp) in seen:
                plan.append((rel, fp, "skipped", None, None, None, None, None))
                continue
            try:
                stats, found = scan_path(p, use_llm=use_llm, display_name=rel)
                plan.append((rel, fp, "scanned", st.st_size, mtime, stats["records"], "", found))
                log(f"  فُحص: {rel} ({len(found)} نتائج)")
            except UnreadableFile as e:
                plan.append((rel, fp, "failed", st.st_size, mtime, 0, str(e), []))
            except Exception:  # noqa: BLE001  (ملف تالف: نكمل الباقي)
                plan.append((rel, fp, "failed", st.st_size, mtime, 0, "تعذّرت قراءته", []))
        STATUS.update(done=len(files), current="حفظ النتائج")

        counts = {a: sum(1 for x in plan if x[2] == a) for a in ("scanned", "skipped", "failed")}
        with wh.connect() as con:
            con.execute("BEGIN")
            run_id = con.execute("SELECT nextval('seq_run')").fetchone()[0]
            for rel, fp, action, size, mtime, records, error, found in plan:
                row = con.execute("SELECT file_id FROM dim_file WHERE folder = ? AND rel_path = ?", (folder, rel)).fetchone()
                file_id = row[0] if row else con.execute("SELECT nextval('seq_file')").fetchone()[0]
                if not row:
                    con.execute("INSERT INTO dim_file VALUES (?, ?, ?, ?)", (file_id, folder, rel, started))
                if action != "skipped":
                    con.execute("INSERT OR REPLACE INTO file_version VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (file_id, fp, size, mtime, started, records, error))
                    con.execute("DELETE FROM fact_finding WHERE file_id = ? AND fingerprint = ?", (file_id, fp))
                    con.executemany("INSERT INTO fact_finding VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                        (file_id, fp, f["sheet"], f["column"], f["pii_type"], f["rows"], f["confidence"],
                         f["method"], f["sample"], f.get("context", "")) for f in found])
                con.execute("INSERT INTO run_file VALUES (?, ?, ?, ?)", (run_id, file_id, fp, action))
            con.execute("INSERT INTO scan_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (run_id, folder, trigger, started, datetime.now(), len(files),
                         counts["scanned"], counts["skipped"], counts["failed"], "done"))
            con.execute("COMMIT")
        summary = {"run_id": run_id, "files": len(files), **counts,
                   "seconds": round((datetime.now() - started).total_seconds())}
        log(f"تم الفحص رقم {run_id}: {len(files)} ملف — فُحص {counts['scanned']}، "
            f"تُخطّي {counts['skipped']} (ما تغيّر)، تعذّر {counts['failed']}")
        return summary
    finally:
        STATUS.update(running=False, current="")
        _LOCK.release()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("folder", nargs="?", default=None, help="المجلد (افتراضيًا المجلد المحفوظ من الموقع)")
    p.add_argument("--no-llm", action="store_true")
    a = p.parse_args()
    folder = a.folder or wh.get_folder()
    if not folder:
        raise SystemExit("حدد المجلد: python -m sanad.pipeline.incremental \"C:\\path\\to\\folder\"")
    t0 = time.time()
    run_scan(folder, use_llm=not a.no_llm, trigger="manual")
    print(f"({time.time() - t0:.0f} ثانية)")


if __name__ == "__main__":
    main()