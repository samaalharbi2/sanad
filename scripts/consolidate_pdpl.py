"""يدمج تعديلات 2023 على النص الأصلي لنظام حماية البيانات الشخصية (2021)،
ويطلع النص الساري مع توثيق مصدر كل مادة.

المدخلات (في data/raw/regulations/sources/):
  pdpl_law_original_2021.txt   النص الأصلي (من هيئة الخبراء)
  pdpl_amendments_2023.txt     تعديلات المرسوم م/148 (من جريدة أم القرى)
المخرج:
  data/raw/regulations/pdpl_law.txt

التشغيل:  python scripts/consolidate_pdpl.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "raw" / "regulations" / "sources"
OUT = ROOT / "data" / "raw" / "regulations" / "pdpl_law.txt"

AMENDED = "[معدّلة بموجب المرسوم الملكي رقم (م/148) وتاريخ 5/9/1444هـ]"
REPEALED = "[ملغاة بموجب المرسوم الملكي رقم (م/148) وتاريخ 5/9/1444هـ]"
NOISE = {"تعديلات المادة", "رئيس مجلس الوزراء", "نظام حماية البيانات الشخصية"}


# ---------- قراءة النص الأصلي إلى مواد ----------
def load_articles(path):
    articles, order, current = {}, [], None
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line in NOISE:
            continue
        if re.fullmatch(r"المادة [؀-ۿ ]+", line):
            current = line.replace("المادة ", "", 1)
            articles[current], order = [], order + [current]
        elif current:
            articles[current].append(line)
    return articles, order


# ---------- قراءة بنود التعديل ----------
def load_amendments(path):
    items, num = {}, None
    start = re.compile(r"^(\d+)- (تعديل|إحلال|إضافة|إلغاء)")
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        m = start.match(line.strip())
        if m:
            num = int(m.group(1))
            items[num] = []
        if num:
            items[num].append(line.strip())
    return {n: "\n".join(v) for n, v in items.items()}


def quote(block):
    """النص بين أول « وآخر »."""
    return block[block.index("«") + 1 : block.rindex("»")].strip()


def quotes(block):
    return [q.strip() for q in re.findall(r"«(.*?)»", block, flags=re.S)]


# ---------- أدوات التعديل (كل وحدة تتأكد إن النص القديم موجود) ----------
def replace_line(art, starts_with, new):
    idx = [i for i, l in enumerate(art) if l.startswith(starts_with)]
    assert len(idx) == 1, f"لم أجد سطرًا واحدًا يبدأ بـ: {starts_with}"
    art[idx[0]] = new


def replace_word(art, old, new):
    text = "\n".join(art)
    assert text.count(old) == 1, f"الكلمة '{old}' ليست موجودة مرة واحدة"
    art[:] = text.replace(old, new).split("\n")


def main():
    arts, order = load_articles(SRC / "pdpl_law_original_2021.txt")
    am = load_amendments(SRC / "pdpl_amendments_2023.txt")
    assert len(order) == 43, f"المتوقع 43 مادة، الموجود {len(order)}"
    assert len(am) == 27, f"المتوقع 27 تعديلًا، الموجود {len(am)}"

    status = {name: "original" for name in order}

    def full(name, item):
        arts[name] = quote(am[item]).split("\n")
        status[name] = "amended"

    def mark(name):
        status[name] = "amended"

    # 1-4: تعريفات المادة الأولى
    replace_line(arts["الأولى"], "الإتلاف:", quote(am[1]))
    replace_line(arts["الأولى"], "الإفصاح:", quote(am[2]))
    sensitive = quote(am[3]).replace("البيانات الحساسة: «", "البيانات الحساسة: ")
    replace_line(arts["الأولى"], "البيانات الحساسة:", sensitive)
    replace_line(arts["الأولى"], "صاحب البيانات الشخصية:", quote(am[4]))
    mark("الأولى")
    full("الرابعة", 5)
    replace_word(arts["الخامسة"], "كتابية", "صريحة"); mark("الخامسة")        # 6
    arts["السادسة"].append(quote(am[7])); mark("السادسة")                   # 7
    full("الثامنة", 8)
    # 9: الفقرة (1) من التاسعة = السطور حتى البند (ب)
    a9 = arts["التاسعة"]
    b = next(i for i, l in enumerate(a9) if l.startswith("ب-"))
    arts["التاسعة"] = quote(am[9]).split("\n") + a9[b + 1 :]; mark("التاسعة")
    full("العاشرة", 10)
    replace_line(arts["الحادية عشرة"], "إذا اتضح أن", quote(am[11])); mark("الحادية عشرة")
    full("الثانية عشرة", 12)
    q13 = quotes(am[13])                                                    # 13
    replace_line(arts["الثالثة عشرة"], "على جهة التحكم، في حالة جمع", q13[0].rstrip(".:…") + ":")
    replace_line(arts["الثالثة عشرة"], "المسوغ النظامي أو العملي", q13[1]); mark("الثالثة عشرة")
    full("الخامسة عشرة", 14)
    replace_line(arts["السادسة عشرة"], "على جهة التحكم ألاّ تفصح", quote(am[15]).rstrip(".:…") + ":")
    mark("السادسة عشرة")
    replace_line(arts["الثامنة عشرة"], "على جهة التحكم إتلاف", quote(am[16])); mark("الثامنة عشرة")
    full("العشرون", 17)
    replace_word(arts["الرابعة والعشرون"], "الكتابية", "الصريحة"); mark("الرابعة والعشرون")  # 18
    full("التاسعة والعشرون", 19)
    full("الثلاثون", 20)
    arts["الثانية والثلاثون"], status["الثانية والثلاثون"] = [], "repealed"  # 21
    full("الثالثة والثلاثون", 22)
    full("الخامسة والثلاثون", 23)
    replace_line(arts["السادسة والثلاثون"], "تكوّن بقرار", quote(am[24])); mark("السادسة والثلاثون")
    full("السابعة والثلاثون", 25)
    full("الثانية والأربعون", 26)
    full("الثالثة والأربعون", 27)

    # ---------- الكتابة ----------
    out = [
        "نظام حماية البيانات الشخصية (النص الساري بعد دمج التعديلات)",
        "الصادر بالمرسوم الملكي رقم (م/19) وتاريخ 9/2/1443هـ، والمعدّل بالمرسوم الملكي رقم (م/148) وتاريخ 5/9/1444هـ",
        "",
    ]
    for name in order:
        out.append(f"المادة {name}")
        if status[name] == "amended":
            out.append(AMENDED)
        elif status[name] == "repealed":
            out.append(REPEALED)
        out.extend(arts[name])
        out.append("")
    OUT.write_text("\n".join(out), encoding="utf-8")

    counts = {s: list(status.values()).count(s) for s in ("original", "amended", "repealed")}
    print(f"تم: {OUT.relative_to(ROOT)}")
    print(f"  مواد بدون تعديل: {counts['original']}")
    print(f"  مواد معدّلة:     {counts['amended']}")
    print(f"  مواد ملغاة:      {counts['repealed']}")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as e:
        sys.exit(f"توقف الدمج: {e}")
