"""يفحص جاهزية بيئة العمل خطوة بخطوة ويقول لك وش الناقص.

التشغيل:  python scripts/check_setup.py
"""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OK, FAIL = "  [تم]  ", "  [ناقص]"
problems = 0


def report(ok: bool, msg: str, fix: str = "") -> None:
    global problems
    print((OK if ok else FAIL) + " " + msg)
    if not ok:
        problems += 1
        if fix:
            print("           الحل: " + fix)


print("\n١) إصدار Python")
v = sys.version_info
report(v >= (3, 10), f"Python {v.major}.{v.minor}", "ثبّت Python 3.11 من python.org")

print("\n٢) المكتبات")
for module, pkg in [("yaml", "pyyaml"), ("dotenv", "python-dotenv"), ("pandas", "pandas"),
                    ("pymupdf", "pymupdf"), ("ollama", "ollama"), ("chromadb", "chromadb"),
                    ("duckdb", "duckdb"), ("faker", "faker")]:
    try:
        importlib.import_module(module)
        report(True, pkg)
    except ImportError:
        report(False, pkg, "فعّل البيئة الافتراضية ثم: pip install -r requirements.txt")

print("\n٣) المجلدات")
try:
    from sanad.config import load_settings, path
    settings = load_settings()
    for key in ["regulations_raw", "processed", "test_data"]:
        p = path(key)
        p.mkdir(parents=True, exist_ok=True)
        report(True, str(p.relative_to(ROOT)))
except Exception as e:  # noqa: BLE001
    settings = None
    report(False, f"قراءة الإعدادات: {e}", "تأكد إن config/settings.yaml موجود")

print("\n٤) Ollama والنماذج")
if settings:
    try:
        import ollama
        client = ollama.Client(host=settings["ollama"]["host"])
        resp = client.list()
        models = resp.get("models", []) if isinstance(resp, dict) else resp.models
        names = {(m.get("model") or m.get("name")) if isinstance(m, dict) else m.model for m in models}
        report(True, "Ollama شغّال")
        for key in ["chat_model", "embed_model"]:
            want = settings["ollama"][key]
            found = any(n == want or n.startswith(want + ":") or n == want + ":latest" for n in names)
            report(found, f"النموذج {want}", f"ollama pull {want}")
    except Exception:  # noqa: BLE001
        report(False, "Ollama غير متاح", "ثبّت Ollama من ollama.com وتأكد إنه شغّال")

print("\n٥) ملفات الأنظمة")
if settings:
    pdfs = list(path("regulations_raw").glob("*.pdf"))
    report(len(pdfs) > 0, f"{len(pdfs)} ملف PDF في data/raw/regulations",
           "حمّل نظام حماية البيانات الشخصية ولوائحه من موقع سدايا وحطها هنا")

print("\n" + ("كل شيء جاهز ✓" if problems == 0 else f"باقي {problems} خطوة. اتبع الحلول فوق ثم أعد التشغيل."))
