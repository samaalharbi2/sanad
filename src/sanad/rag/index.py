"""يحوّل القطع إلى متجهات بنموذج bge-m3 ويخزنها في Chroma.

التشغيل:  python -m sanad.rag.index
المدخل:   data/processed/chunks.jsonl
الناتج:   data/chroma/  (قاعدة المتجهات)
"""
import json
import time

import chromadb
import ollama
from chromadb.config import Settings

from sanad.config import load_settings, path

COLLECTION = "pdpl"
BATCH = 8  # دفعات صغيرة عشان جهاز بذاكرة 8 جيجا


def get_collection(reset=False):
    client = chromadb.PersistentClient(
        path=str(path("chroma")), settings=Settings(anonymized_telemetry=False)
    )
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:  # noqa: BLE001  (المجموعة غير موجودة)
            pass
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def main():
    s = load_settings()
    llm = ollama.Client(host=s["ollama"]["host"])
    model = s["ollama"]["embed_model"]

    chunks = [json.loads(l) for l in path("processed").joinpath("chunks.jsonl").open(encoding="utf-8")]
    # المواد الملغاة ما تنفهرس: ما نبي سَنَد يستشهد بها أبدًا
    chunks = [c for c in chunks if c["status"] != "repealed"]
    col = get_collection(reset=True)

    t0 = time.time()
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        resp = llm.embed(model=model, input=[c["text"] for c in batch])
        col.add(
            ids=[c["id"] for c in batch],
            embeddings=resp["embeddings"],
            documents=[c["text"] for c in batch],
            metadatas=[{k: c[k] for k in ("doc", "doc_title", "article", "article_title", "status", "part")}
                       for c in batch],
        )
        print(f"  {min(i + BATCH, len(chunks))}/{len(chunks)}", end="\r")
    print(f"\nتم فهرسة {col.count()} قطعة في {time.time() - t0:.0f} ثانية")


if __name__ == "__main__":
    main()
