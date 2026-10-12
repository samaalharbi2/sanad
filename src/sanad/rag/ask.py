"""اسأل سَنَد سؤالًا عن نظام حماية البيانات الشخصية.

التشغيل:
  python -m sanad.rag.ask "هل يجوز نقل البيانات الصحية خارج المملكة؟"
  python -m sanad.rag.ask "..." --show      (يعرض القطع اللي استرجعها)
"""
import argparse
import time

import ollama

from sanad.config import load_settings
from sanad.rag.index import get_collection

TOP_K = 4

SYSTEM = """أنت «سَنَد»، مساعد امتثال لنظام حماية البيانات الشخصية في المملكة العربية السعودية.
القواعد:
1. أجب فقط من النصوص المرفقة. لا تستخدم أي معلومة من خارجها.
2. بعد كل معلومة اذكر مصدرها بين قوسين بهذا الشكل: (اسم الوثيقة، المادة ...).
3. إذا لم تجد الإجابة في النصوص المرفقة فقل بالضبط: «لم أجد في المصادر المتاحة نصًا يجيب على هذا السؤال.»
4. أجب بالعربية، باختصار ووضوح."""


def retrieve(question, k=TOP_K):
    s = load_settings()
    llm = ollama.Client(host=s["ollama"]["host"])
    q_vec = llm.embed(model=s["ollama"]["embed_model"], input=[question])["embeddings"][0]
    res = get_collection().query(query_embeddings=[q_vec], n_results=k)
    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        hits.append({"text": doc, "meta": meta, "score": 1 - dist})
    return hits


def answer(question, hits):
    s = load_settings()
    llm = ollama.Client(host=s["ollama"]["host"])
    context = "\n\n---\n\n".join(h["text"] for h in hits)
    resp = llm.chat(
        model=s["ollama"]["chat_model"],
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"النصوص:\n{context}\n\nالسؤال: {question}"},
        ],
        options={"temperature": s["ollama"]["temperature"]},
    )
    return resp["message"]["content"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--show", action="store_true", help="اعرض القطع المسترجعة")
    args = p.parse_args()

    t0 = time.time()
    hits = retrieve(args.question)
    if args.show:
        for h in hits:
            print(f"[{h['score']:.2f}] {h['text'][:200]}\n")
    print(answer(args.question, hits))
    print("\nالمصادر:")
    for h in hits:
        m = h["meta"]
        tag = " (معدّلة)" if m["status"] == "amended" else ""
        print(f"  - {m['doc_title']}، المادة {m['article']}{tag}  [تشابه {h['score']:.2f}]")
    print(f"\n({time.time() - t0:.0f} ثانية)")


if __name__ == "__main__":
    main()
