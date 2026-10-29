# NOMIKO v0.9.0 — автоматичне перенесення вихідного коду

Повний вихідний код NOMIKO v0.9.0 уже підготовлений у чаті як `NOMIKO-v0.9.0-GitHub-AutoUploader.zip`.

Підключення GitHub не підтримує пряме перенесення локального ZIP на GitHub. Тому зроблено безпечний Windows-завантажувач для одноразового імпорту **всіх 46 файлів** — без необхідності вручну завантажувати кожну папку.

1. Завантажити цей ZIP з поточної розмови, розпакувати на Windows 11.
2. Запустити `UPLOAD_TO_GITHUB.bat`.
3. За потреби дозволити встановити Git і GitHub CLI через WinGet, увійти **саме в flekideveloper** через офіційний GitHub.
4. Скрипт сам копіює тільки вихідні файли NOMIKO, робить commit/push до `main` і запускає тестову Windows-збірку в GitHub Actions.

**Не потрібно** передавати токен або приватний ключ у цей чат. Раніше доданий секрет `NOMIKO_SIGNING_KEY_B64` залишається у GitHub Secrets. Не створювати тег релізу, доки Windows-збірку не перевірено.

---
# NOMIKO v0.9.0 — підключення автооновлень

Репозиторій: https://github.com/flekideveloper/nomiko-updates

## 1. Код
Розпакуй `NOMIKO-Windows11-v0.9.0-update-system.zip`. У GitHub додай до кореня репозиторію **вміст папки `NOMIKO-Windows11`**, а не сам ZIP. Потрібні `main.py`, `requirements.txt`, `src/`, `tests/`, `installer/`, `tools/`, `update_helper.py` та решта файлів. Workflow уже присутній у репозиторії.

## 2. Секрет підписування
Відкрий Settings → Secrets and variables → Actions → New repository secret.
Назва: `NOMIKO_SIGNING_KEY_B64`.
Значення: **лише Base64-рядок** із раніше збереженого приватного файлу ключа.
Не публікуй приватний ключ у коді чи листуванні.

## 3. Перша тестова Windows-збірка
У вкладці Actions відкрий `NOMIKO Windows build and signed release` → `Run workflow` (`main`). Отримаєш CI artifact, але це **ще не реліз**.

## 4. Після тестування
Коли EXE реально працюватиме на Windows 11, створимо git-тег `v0.9.0-alpha` і опублікуємо підписаний реліз. Щоб перевірити автооновлення на практиці, створимо наступний реліз `v0.9.1-alpha`.

**Важливо:** без протестованого EXE, доданого секрету та підписаного GitHub Release автооновлення ще не працюють.
