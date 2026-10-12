"""الفحص الليلي المجدول (Prefect).

  python -m sanad.pipeline.nightly            يشغّل الفحص مرة وحدة الحين (عبر Prefect)
  python -m sanad.pipeline.nightly --serve    يبقى شغّال ويفحص كل ليلة الساعة 2 الفجر (بتوقيت الرياض)

ليش Prefect؟ يجدول التشغيل، ويعيد المحاولة لو فشل الفحص (مثلًا Ollama كان مطفي)،
ويحفظ سجل كل تشغيل: متى بدأ، وكم أخذ، ونجح أو فشل.
"""
import argparse
import os

# نطفي إحصاءات الاستخدام في Prefect (ما نحتاجها، وتسبب رسالة خطأ مزعجة أول تشغيل)
os.environ.setdefault("PREFECT_SERVER_ANALYTICS_ENABLED", "false")

from sanad.pipeline import warehouse as wh
from sanad.pipeline.incremental import run_scan

try:
    from prefect import flow, get_run_logger, task
    from prefect.schedules import Cron
except ImportError:  # بدون Prefect: نشغّل الفحص مباشرة
    flow = task = None


if flow:
    @task(name="فحص الملفات الجديدة والمتغيرة", retries=2, retry_delay_seconds=300)
    def scan_task(folder: str):
        logger = get_run_logger()
        return run_scan(folder, use_llm=True, trigger="nightly", log=logger.info)

    @flow(name="sanad-nightly-scan", log_prints=True)
    def nightly_scan(folder: str = ""):
        folder = folder or wh.get_folder()
        if not folder:
            raise ValueError("ما فيه مجلد مراقب. حدده من صفحة «المراقبة الدورية» في الموقع.")
        return scan_task(folder)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--serve", action="store_true", help="جدولة يومية الساعة 2 الفجر")
    p.add_argument("--folder", default="")
    a = p.parse_args()
    folder = a.folder or wh.get_folder()
    if not flow:
        if a.serve:
            raise SystemExit("الجدولة تحتاج Prefect:  pip install prefect")
        run_scan(folder, trigger="manual")
        return
    if a.serve:
        print("سَنَد يراقب المجلد كل ليلة الساعة 2 الفجر. خلّ هذي النافذة مفتوحة (Ctrl+C للإيقاف).")
        nightly_scan.serve(name="sanad-nightly", parameters={"folder": folder},
                           schedules=[Cron("0 2 * * *", timezone="Asia/Riyadh")])
    else:
        nightly_scan(folder)


if __name__ == "__main__":
    main()