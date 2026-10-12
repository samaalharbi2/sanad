# سَنَد (Sanad)

مساعد امتثال لنظام حماية البيانات الشخصية في المملكة. يكتشف البيانات الشخصية في الجداول والملفات، ويصنّفها، ويجاوب عن النظام مع رقم المادة. كل شيء يعمل محليًا على Ollama.

## هيكل المشروع

```
sanad/
├── config/settings.yaml      إعدادات المشروع (النماذج، المسارات)
├── data/
│   ├── raw/regulations/      ملفات PDF للأنظمة (تضعها يدويًا)
│   ├── processed/            النصوص المستخرجة والمقطّعة
│   └── test/                 بيانات اختبار وهمية فقط
├── src/sanad/
│   ├── config.py             قراءة الإعدادات
│   ├── ingest/               استخراج النص من PDF
│   ├── rag/                  البحث والإجابة (لاحقًا)
│   └── pii/                  كشف البيانات الشخصية (لاحقًا)
├── scripts/check_setup.py    فحص جاهزية البيئة
├── tests/                    الاختبارات
└── notebooks/                تجارب
```

## التشغيل لأول مرة

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# Mac / Linux:  source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python scripts/check_setup.py
```

## قاعدة مهمة

لا تضع أي بيانات شخصية حقيقية في هذا المشروع. كل بيانات الاختبار وهمية.
