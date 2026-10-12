"""ينظف نصًا منسوخًا من صفحة في جريدة أم القرى (uqn.gov.sa):
يشيل قوائم الموقع وأزراره، ويبقي العنوان وتاريخ النشر والمواد بس.

التشغيل:
  python scripts/clean_uqn_paste.py <الملف المنسوخ> <اسم الملف الناتج> [رابط الصفحة]
مثال:
  python scripts/clean_uqn_paste.py raw.txt pdpl_implementing_regulation.txt https://www.uqn.gov.sa/details?p=23595
الناتج يُحفظ في: data/raw/regulations/
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "regulations"
START_MARK = "Shrink Font Icon"   # يظهر مباشرة بعد العنوان والتاريخ
END_MARK = "اقرأ أيضاً"            # أول شيء بعد نهاية المحتوى


def clean(raw: str, url: str = "") -> tuple[str, list[str]]:
    # نشيل المحارف الخفية (مثل U+200C) اللي يضيفها الموقع بعد بعض الحروف
    raw = raw.replace("\u200c", "").replace("\u200f", "")
    lines = [l.rstrip() for l in raw.splitlines()]
    start = next(i for i, l in enumerate(lines) if l.strip().startswith(START_MARK))
    end = next((i for i, l in enumerate(lines) if l.strip() == END_MARK), len(lines))
    title, date = lines[start - 2].strip(), lines[start - 1].strip()
    body = [l for l in lines[start + 1 : end]]
    while body and not body[-1].strip():
        body.pop()

    header = [title, f"تاريخ النشر في جريدة أم القرى: {date}"]
    if url:
        header.append(f"المصدر: {url}")
    articles = [l.strip() for l in body if re.match(r"^المادة [؀-ۿ ]+(:|$)", l.strip())]
    return "\n".join(header + [""] + body) + "\n", articles


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, name = Path(sys.argv[1]), sys.argv[2]
    url = sys.argv[3] if len(sys.argv) > 3 else ""
    text, articles = clean(src.read_text(encoding="utf-8-sig"), url)
    out = OUT_DIR / name
    out.write_text(text, encoding="utf-8")
    print(f"تم: {out.relative_to(ROOT)}  ({len(text):,} حرف)")
    print(f"  عدد المواد: {len(articles)}")
    if articles:
        print(f"  أول مادة: {articles[0]}")
        print(f"  آخر مادة: {articles[-1]}")


if __name__ == "__main__":
    main()
