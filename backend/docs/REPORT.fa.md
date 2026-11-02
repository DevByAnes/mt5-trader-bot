# گزارش تحویل B1 — ۲۰۲۶-۱۱-۰۲

۱) **فاز ۰:** نسخه‌های پایدار از Python.org و صفحات رسمی بسته‌ها در PyPI بررسی شدند: Python 3.15.2، FastAPI 0.162.0، Pydantic 2.14.2، Uvicorn 0.54.0، uv 0.13.6، Ruff 0.17.3، mypy 2.4.1، pytest 9.2.0، Hypothesis 6.170.14، Schemathesis 4.33.0 و datamodel-code-generator 0.87.0. اجرای محلی با Python 3.14.10 انجام شد؛ دلیل انتخاب، شاخهٔ پایدارِ تحت نگهداری و سازگاری بسته‌هاست. جدول منابع و گزینه‌های منسوخِ کنارگذاشته‌شده در [PHASE0.md](PHASE0.md) است. بسته‌های منتخب در `uv.lock` قفل شده‌اند.

۲) **فایل‌ها:** اسکلت `backend/` شامل `pyproject.toml`، `uv.lock`، نسخهٔ Python، راهنمای اجرا، API، مدل‌های تولیدشده، بارگذار Fixture، شبیه‌ساز حافظه‌ای، WebSocket و امنیت ایجاد شد. تست‌ها، ابزار بازتولید مدل، lint گارد سفارش، نمونهٔ اثبات شکست گارد، smoke واقعی CLI و ابزار ثبت خروجی بررسی‌ها اضافه شدند. ماژول‌های `bridge/data/analysis/validation/storage` فقط README و marker Protocol دارند. فایل workflow بک‌اند و ignore کش‌های Python اضافه شد. فهرست دقیق در [FILES.md](FILES.md) است. هیچ فایل `schema/`، Fixture ریشه، فرانت یا `docs/CONTRACT.md` تغییر نکرده است؛ `git diff --exit-code -- schema fixtures docs/CONTRACT.md src` با خروج صفر تأیید شد.

۳) **پذیرش و خروجی واقعی:** متن کامل خروجی‌ها در [VERIFICATION.txt](VERIFICATION.txt) ثبت شده است.

| معیار | نتیجه | خروجی واقعی / دامنهٔ اعتبار |
|---|---|---|
| Ruff | پاس | `All checks passed!` |
| mypy strict | پاس | `Success: no issues found in 50 source files`؛ شامل src، tools و tests |
| pytest | پاس | `116 passed in 12.34s`؛ شامل همهٔ موارد زیر |
| Schemathesis | پاس با تنظیم صریح | هر ۱۷ عملیات روی HTTP واقعی؛ ۲۵ مثال در هر عملیات به‌علاوهٔ coverage؛ اجرای جداگانه `17 passed in 5.96s` |
| Fixture و پاسخ همهٔ endpointها | پاس | اعتبارسنجی envelope و مقایسهٔ داده با Fixture؛ فقط ساعت سلامت/مرز روز در شبیه‌ساز به‌روز می‌شود |
| بازتولید و هم‌ترازی مدل | پاس | `Generated models match frozen schemas`؛ مقایسهٔ فایل و هش، خواص enum/step و optional≠nullable |
| Idempotency / نسخهٔ هم‌زمان | پاس | replay دقیق پذیرش قبلی، canonical body، کلید با بدنه/endpoint متفاوت 409، فقط یک پذیرش نسخه |
| توکن / CORS / rate limit / خطا | پاس | 401 بدون توکن، رد Origin/Host/peer خارجی، 503 محدودیت طبق وضعیت‌های موجود قرارداد، خطای داخلی بدون جزئیات |
| Realtime و قطع اتصال | پاس | ۹ تست: ترتیب و reset توالی، replay، هر ۸ نوع رویداد، gap، قطع ناگهانی، پاکسازی منابع، صف پر و مهلت ارسال |
| Snapshot کامل | مطابق قرارداد فعلی | replay نوع‌های مجاز telemetry + دریافت همهٔ منابع REST؛ رویداد جدید `snapshot` یا Snapshot اتمی اختراع نشده است |
| endpoint سناریو در production | پاس | درخواست احرازشده به `/__dev/scenario` در production پاسخ 404 دارد |
| گارد سفارش | پاس | `No execution symbols in src`؛ نمونهٔ بد: `bad.py:1: execution symbol` و `exit code: 1 (expected 1)` |
| راه‌اندازی واقعی CLI | پاس | توکن env و stdin: `HTTP=200, missing token=401, WS heartbeat seq=1`؛ فرایند پس از آزمایش متوقف شد |
| lockfile | پاس | `uv lock --check` خروج صفر؛ ۷۰ بسته resolve شده‌اند |
| CI ویندوز/لینوکس | پیکربندی شده | workflow اضافه شده؛ اجرای hosted در این گزارش پاس فرض نمی‌شود |

**استثنای روشن Schemathesis:** در Schema فعلی، Cursor یک رشتهٔ بدون قالب و `position_id` اختیاری است. بنابراین بررسی پیش‌فرض positive-data-acceptance، بعضی خطاهای معنایی معتبر `422` را شکست می‌داند. فقط ۶ عملیات مرتبط، در تنظیمات تست، این پاسخ را می‌پذیرند؛ بررسی پاسخ با Schema، خطای سرور، رد ورودی نامعتبر و امنیت غیرفعال نشده‌اند. اجرای بدون این تنظیم، شکاف CCP-06 را نشان می‌دهد. این یک «پاس بدون قیدِ تنظیمات پیش‌فرض» نیست.

۴) **اجرا و تست:** داخل `backend/`، `uv sync --frozen` و سپس با توکن محیطی یا stdin، `uv run aurum-backend`. نمونهٔ PowerShell تولید توکن تصادفی بدون چاپ آن، در [README](../README.md) آمده است. برای بررسی کامل `uv run python -m tools.verify`؛ دستورات مستقل `uv run ruff check`، `uv run mypy`، `uv run pytest -q`، `uv run python -m tools.gen_models --check`، `uv run aurum-lint` و `uv run python -m tools.smoke` هستند. بازتولید مدل: `uv run python -m tools.gen_models`.

۵) **ASSUMPTIONها:** ویندوز، یک ماشین، یک فرایند و یک نشست؛ بستهٔ اجرایی B1 از checkout مخزن اجرا می‌شود. تست روی Python 3.14.10 است؛ پشتیبانی اعلام‌شدهٔ 3.12–3.15 و لینوکس در این محیط همگی آزمایش نشده‌اند. پذیرش و Ack فقط شبیه‌سازی‌اند؛ تأخیر و مرز COLD شبیه‌سازی‌شده ۷۰۰ms است. حافظه تا reset/exit نگه داشته می‌شود و هیچ دوام پس از restart وجود ندارد. «Python قطع» با 503 و بستن Stream شبیه‌سازی می‌شود، نه خاموش‌کردن خود سرور کنترل سناریو. فیلتر و ترتیب دلخواه که در Schema تعریف نشده پذیرفته نمی‌شود؛ ترتیب جدیدترین‌اول و tie پایدار است.

۶) **پیشنهادهای قرارداد:** شش مورد در [CONTRACT_CHANGE_PROPOSALS.md](../../docs/CONTRACT_CHANGE_PROPOSALS.md): وضعیت‌های 429/500، روش احراز هویت WebSocket مرورگر، دامنهٔ Snapshot، کنترل توسعه، جزئیات لیست/Ack و الزام معنایی Cursor/فرمان تک‌پوزیشن. هیچ‌کدام به‌جای تأیید کاربر در فایل‌های منجمد اعمال نشده‌اند. endpoint کنترل توسعه همان ابزار جداگانهٔ صریحاً خواسته‌شده در درخواست است و به `/api/v1` منجمد افزوده نشده است.

۷) **موارد ناتمام و محدودیت‌ها:** اتصال خود داشبورد مرورگری به WebSocket هنوز آماده نیست؛ مرورگر نمی‌تواند هدر Bearer دلخواه را به handshake اضافه کند و روش native/cookie باید تأیید شود. transport فعلی فقط کلاینت محلیِ قادر به افزودن هدر را می‌پذیرد. Snapshot اتمی یک‌تکه، احراز هویت بومی Rust/Python و وضعیت مؤثر واقعی COLD در قرارداد نهایی نشده‌اند. اجرای wheel مستقل از checkout، restart-durability، lifecycle Sidecar، Keyring و ارتباط EA در این فاز وجود ندارند. هیچ تحلیل معاملاتی، Bridge فایل، EA، MT5 یا SQLite ماندگار پیاده‌سازی نشده است. گارد ایستا یک مانع بررسی کد است؛ اثبات ریاضی در برابر کد مبهم‌سازی‌شده یا تغییرات آینده نیست.

۸) **پیش‌نیاز B2:** بله؛ پیش از B2 باید پیام‌های Bridge، مالکیت احراز هویت و امضا، correlation/Ack و retention، رزرو نسخه، زمان مؤثر COLD، ترتیب Snapshot و seq، و رفتار restart/gap در قرارداد روشن و تأیید شوند. این فاز متوقف می‌شود؛ هیچ کار B2 آغاز نشده است.
