"""اختبارات الفحص التزايدي وقراءة Word وPDF (بدون النموذج، وبمستودع مؤقت)."""
import os
import shutil
from pathlib import Path

import pytest

from sanad.pii.detector import scan_path
from sanad.pii.rules import mask
from sanad.pipeline import incremental, warehouse

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "data" / "test" / "samples"


@pytest.fixture
def tmp_warehouse(tmp_path, monkeypatch):
    """كل اختبار له مستودع DuckDB خاص، عشان ما نلمس بيانات المستخدم."""
    real = warehouse.path

    def fake(key):
        return tmp_path / "sanad.duckdb" if key == "warehouse" else real(key)
    monkeypatch.setattr(warehouse, "path", fake)
    return tmp_path


def write_csv(p, rows):
    p.write_text("name,mobile\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_incremental_skips_unchanged_and_tracks_history(tmp_path, tmp_warehouse):
    folder = tmp_path / "share"
    folder.mkdir()
    write_csv(folder / "a.csv", ["أحمد علي,0551234567", "سارة محمد,0559876543"])
    write_csv(folder / "b.csv", ["خالد,0501112223", "منى,0504445556"])

    first = incremental.run_scan(folder, use_llm=False, log=lambda m: None)
    assert (first["scanned"], first["skipped"]) == (2, 0)

    second = incremental.run_scan(folder, use_llm=False, log=lambda m: None)
    assert (second["scanned"], second["skipped"]) == (0, 2)  # ما تغيّر شي

    os.utime(folder / "a.csv")  # انحفظ بدون تغيير في المحتوى
    (folder / "b.csv").unlink()  # انحذف
    write_csv(folder / "c.csv", ["نورة,0533334445", "فهد,0536667778"])
    third = incremental.run_scan(folder, use_llm=False, log=lambda m: None)
    assert (third["scanned"], third["skipped"], third["files"]) == (1, 1, 2)

    runs = warehouse.runs(str(folder.resolve()))
    assert [r["files_with_pii"] for r in runs] == [2, 2, 2]
    _, files, findings = warehouse.run_detail(runs[-1]["run_id"])
    assert {f["file"] for f in findings} == {"a.csv", "c.csv"}  # b.csv راح من آخر لقطة


@pytest.mark.skipif(not (SAMPLES / "خطاب_تعريف_بالراتب.docx").exists(), reason="شغّل generate_docs أولًا")
def test_word_reads_tables_and_text():
    stats, found = scan_path(SAMPLES / "خطاب_تعريف_بالراتب.docx", use_llm=False)
    kinds = {(f["column"] == "(نص حر)", f["pii_type"]) for f in found}
    assert (False, "NATIONAL_ID") in kinds  # جدول المرافقين
    assert {(True, "NATIONAL_ID"), (True, "IBAN"), (True, "PHONE")} <= kinds  # نص الخطاب


@pytest.mark.skipif(not (SAMPLES / "كشف_المستردات_سبتمبر.pdf").exists(), reason="شغّل generate_docs أولًا")
def test_pdf_table_headers_are_not_reversed():
    stats, found = scan_path(SAMPLES / "كشف_المستردات_سبتمبر.pdf", use_llm=False)
    cols = {f["column"]: f["pii_type"] for f in found}
    assert cols.get("رقم الهوية") == "NATIONAL_ID"
    assert cols.get("الآيبان") == "IBAN"


def test_mask_hides_length():
    assert mask("SA0980663440029787534778") == "S" + "•" * 8 + "8"
    assert mask("1784864884") == "1" + "•" * 8 + "4"