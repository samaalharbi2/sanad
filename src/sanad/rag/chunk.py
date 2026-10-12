"""يقسّم الوثائق إلى قطع: كل مادة قطعة واحدة، مع بياناتها الوصفية.

التشغيل:  python -m sanad.rag.chunk
المدخل:   data/processed/*.jsonl  (ناتج extract_text)
الناتج:   data/processed/chunks.jsonl
"""
import json
import re

from sanad.config import path

# اسم مختصر لكل وثيقة (يظهر في الاستشهاد)
DOC_TITLES = {
    "pdpl_law": "نظام حماية البيانات الشخصية",
    "pdpl_implementing_regulation": "اللائحة التنفيذية لنظام حماية البيانات الشخصية",
    "pdpl_transfer_regulation": "لائحة نقل البيانات الشخصية إلى خارج المملكة",
}
HEADING = re.compile(r"^المادة ([؀-ۿ ]+?)(?:\s*:\s*(.+))?$")
MAX_CHARS = 2500  # المادة الأطول من كذا تنقسم لأجزاء


def split_articles(text):
    """يرجع قائمة مواد: [{name, title, status, body}]"""
    articles, current = [], None
    for line in text.splitlines():
        s = line.strip()
        m = HEADING.match(s)
        if m:
            current = {"name": m.group(1), "title": m.group(2) or "", "status": "original", "lines": []}
            articles.append(current)
        elif current is not None and s:
            if s.startswith("[معدّلة"):
                current["status"] = "amended"
            elif s.startswith("[ملغاة"):
                current["status"] = "repealed"
            else:
                current["lines"].append(s)
    for a in articles:
        a["body"] = "\n".join(a.pop("lines"))
    return articles


def split_long(body):
    """يقسم المادة الطويلة عند حدود الفقرات بدون ما يقطع فقرة."""
    parts, buf = [], ""
    for para in body.split("\n"):
        if buf and len(buf) + len(para) > MAX_CHARS:
            parts.append(buf)
            buf = ""
        buf = f"{buf}\n{para}" if buf else para
    if buf:
        parts.append(buf)
    return parts


def main():
    processed = path("processed")
    chunks = []
    for f in sorted(processed.glob("*.jsonl")):
        if f.stem == "chunks" or f.stem not in DOC_TITLES:
            continue
        text = "\n".join(json.loads(l)["text"] for l in f.open(encoding="utf-8"))
        articles = split_articles(text)
        for a in articles:
            parts = split_long(a["body"]) if a["body"] else [""]
            for i, part in enumerate(parts, start=1):
                label = f"المادة {a['name']}" + (f": {a['title']}" if a["title"] else "")
                chunks.append({
                    "id": f"{f.stem}::{a['name']}::{i}",
                    "doc": f.stem,
                    "doc_title": DOC_TITLES[f.stem],
                    "article": a["name"],
                    "article_title": a["title"],
                    "status": a["status"],
                    "part": i,
                    "parts": len(parts),
                    # النص اللي يتحول لمتجه: اسم الوثيقة + المادة + المحتوى
                    "text": f"{DOC_TITLES[f.stem]}\n{label}\n{part}".strip(),
                })
        print(f"{f.stem}: {len(articles)} مادة")
    out = processed / "chunks.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"المجموع: {len(chunks)} قطعة ← {out.name}")


if __name__ == "__main__":
    main()
