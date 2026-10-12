"""يستخرج النص من ملفات الأنظمة (PDF أو TXT) ويحفظه.

التشغيل:  python -m sanad.ingest.extract_text
الناتج:   data/processed/<اسم الملف>.jsonl
  - PDF: سطر لكل صفحة
  - TXT: سطر واحد للملف كامل
"""
import json

import pymupdf as fitz

from sanad.config import path


def extract_pdf(pdf_path):
    pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            pages.append({"source": pdf_path.name, "page": i, "text": text})
    return pages


def extract_txt(txt_path):
    # utf-8-sig يتعامل مع الملفات اللي يحفظها Notepad بعلامة BOM
    text = txt_path.read_text(encoding="utf-8-sig").strip()
    return [{"source": txt_path.name, "page": 1, "text": text}]


def main():
    raw, out = path("regulations_raw"), path("processed")
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(list(raw.glob("*.pdf")) + list(raw.glob("*.txt")))
    if not files:
        print("ما فيه ملفات PDF أو TXT في", raw)
        return
    for f in files:
        pages = extract_pdf(f) if f.suffix.lower() == ".pdf" else extract_txt(f)
        empty = [p["page"] for p in pages if len(p["text"]) < 30]
        with open(out / f"{f.stem}.jsonl", "w", encoding="utf-8") as fh:
            for p in pages:
                fh.write(json.dumps(p, ensure_ascii=False) + "\n")
        chars = sum(len(p["text"]) for p in pages)
        print(f"{f.name}: {len(pages)} صفحة، {chars:,} حرف")
        if empty:
            # صفحات شبه فارغة = غالبًا صورة ممسوحة وتحتاج OCR
            print(f"   تنبيه: صفحات بدون نص تقريبًا {empty}")
        # تأكد من وجود المواد، مو بس الغلاف
        full = " ".join(p["text"] for p in pages)
        if "المادة الأولى" not in full:
            print("   تنبيه: ما لقيت 'المادة الأولى'. يمكن الملف فيه الغلاف بس بدون المواد")


if __name__ == "__main__":
    main()
