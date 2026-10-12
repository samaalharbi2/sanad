"""مستودع سجل الفحوصات (DuckDB) بنموذج نجمي.

الجداول:
  dim_pii_type   أنواع البيانات: الاسم بالعربي، التصنيف حسب النظام، الخطورة
  dim_file       كل ملف شافه سَنَد في المجلد المراقب (مرة وحدة لكل مسار)
  file_version   نسخة الملف: بصمة المحتوى (SHA-256) + الحجم + آخر تعديل
  fact_finding   الاكتشافات لكل نسخة ملف (تُحسب مرة وحدة لكل محتوى)
  scan_runs      كل عملية فحص: متى، وكم ملف فُحص وكم تُخطّي
  run_file       أي نسخة من كل ملف كانت موجودة في كل فحص، ووش صار لها

الفكرة: الاكتشافات مربوطة بـ«محتوى» الملف مو بالفحص. فلو الملف ما تغيّر، الفحص الجديد
يربط نفس النسخة بدون ما يعيد فحصها، والسجل يبقى كامل لكل ليلة.
"""
import json
import time
from contextlib import contextmanager

import duckdb

from sanad.config import path
from sanad.pii.detector import TYPES

SCHEMA = """
CREATE SEQUENCE IF NOT EXISTS seq_run START 1;
CREATE SEQUENCE IF NOT EXISTS seq_file START 1;
CREATE TABLE IF NOT EXISTS dim_pii_type (
  pii_type VARCHAR PRIMARY KEY, label_ar VARCHAR, category VARCHAR, risk VARCHAR);
CREATE TABLE IF NOT EXISTS dim_file (
  file_id INTEGER PRIMARY KEY, folder VARCHAR, rel_path VARCHAR, first_seen TIMESTAMP,
  UNIQUE (folder, rel_path));
CREATE TABLE IF NOT EXISTS file_version (
  file_id INTEGER, fingerprint VARCHAR, size_bytes BIGINT, modified_at TIMESTAMP,
  scanned_at TIMESTAMP, records INTEGER, error VARCHAR, PRIMARY KEY (file_id, fingerprint));
CREATE TABLE IF NOT EXISTS fact_finding (
  file_id INTEGER, fingerprint VARCHAR, sheet VARCHAR, column_name VARCHAR, pii_type VARCHAR,
  rows INTEGER, confidence VARCHAR, method VARCHAR, sample VARCHAR, context VARCHAR);
CREATE TABLE IF NOT EXISTS scan_runs (
  run_id INTEGER PRIMARY KEY, folder VARCHAR, trigger VARCHAR, started_at TIMESTAMP, finished_at TIMESTAMP,
  files_total INTEGER, files_scanned INTEGER, files_skipped INTEGER, files_failed INTEGER, status VARCHAR);
CREATE TABLE IF NOT EXISTS run_file (
  run_id INTEGER, file_id INTEGER, fingerprint VARCHAR, action VARCHAR);

-- لقطة كاملة لاكتشافات كل فحص (حتى الملفات اللي ما تغيّرت)
CREATE OR REPLACE VIEW v_run_findings AS
SELECT rf.run_id, d.rel_path AS file, f.sheet, f.column_name AS "column", f.pii_type,
       t.label_ar, t.category, t.risk, f.confidence, f.rows, f.sample, f.context, f.method,
       v.modified_at
FROM run_file rf
JOIN fact_finding f USING (file_id, fingerprint)
JOIN dim_file d USING (file_id)
JOIN file_version v USING (file_id, fingerprint)
JOIN dim_pii_type t USING (pii_type);

-- مؤشرات كل فحص (للخط الزمني)
CREATE OR REPLACE VIEW v_run_summary AS
SELECT r.run_id, r.started_at, r.finished_at, r.trigger, r.status,
       r.files_total, r.files_scanned, r.files_skipped, r.files_failed,
       COUNT(DISTINCT x.file)                                         AS files_with_pii,
       COUNT(DISTINCT CASE WHEN x.risk = 'عالية' THEN x.file END)     AS files_high_risk,
       COALESCE(SUM(x.rows), 0)                                       AS values_total,
       COALESCE(SUM(CASE WHEN x.category = 'بيانات حساسة' THEN x.rows END), 0) AS values_sensitive
FROM scan_runs r LEFT JOIN v_run_findings x USING (run_id)
GROUP BY ALL;
"""


@contextmanager
def connect(read_only=False, attempts=20):
    """اتصال قصير بالمستودع. لو عملية ثانية ماسكة الملف (مثل الفحص الليلي)، ننتظر شوي ونعيد."""
    db = path("warehouse")
    db.parent.mkdir(parents=True, exist_ok=True)
    for i in range(attempts):
        try:
            con = duckdb.connect(str(db), read_only=read_only and db.exists())
            break
        except duckdb.IOException:
            if i == attempts - 1:
                raise
            time.sleep(0.5)
    try:
        yield con
    finally:
        con.close()


def init():
    with connect() as con:
        con.execute(SCHEMA)
        con.executemany("INSERT OR REPLACE INTO dim_pii_type VALUES (?, ?, ?, ?)",
                        [(k, *v) for k, v in TYPES.items()])


# ---------- المجلد المراقب ----------
def _monitor_file():
    return path("processed").parent / "monitor.json"


def get_folder():
    f = _monitor_file()
    return json.loads(f.read_text(encoding="utf-8")).get("folder", "") if f.exists() else ""


def set_folder(folder):
    f = _monitor_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"folder": folder}, ensure_ascii=False), encoding="utf-8")


# ---------- قراءة السجل ----------
def _rows(con, sql, params=()):
    cur = con.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def runs(folder, limit=30):
    init()
    with connect() as con:
        rows = _rows(con, """SELECT s.* FROM v_run_summary s JOIN scan_runs r USING (run_id)
                             WHERE r.folder = ? ORDER BY run_id DESC LIMIT ?""", (folder, limit))
    return list(reversed(rows))


def run_detail(run_id):
    with connect() as con:
        findings = _rows(con, "SELECT * FROM v_run_findings WHERE run_id = ? ORDER BY file, sheet", (run_id,))
        files = _rows(con, """
            SELECT d.rel_path AS name, rf.action, v.records, v.error, v.modified_at,
                   (SELECT COUNT(*) FROM fact_finding f WHERE f.file_id = rf.file_id AND f.fingerprint = rf.fingerprint) AS found
            FROM run_file rf JOIN dim_file d USING (file_id)
            LEFT JOIN file_version v USING (file_id, fingerprint)
            WHERE rf.run_id = ? ORDER BY d.rel_path""", (run_id,))
        meta = _rows(con, "SELECT * FROM v_run_summary WHERE run_id = ?", (run_id,))
    return (meta[0] if meta else None), files, findings