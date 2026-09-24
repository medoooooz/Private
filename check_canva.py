import os
import requests
from playwright.sync_api import sync_playwright

# === إعدادات ===
URL = os.getenv("WEBSITE_URL", "https://bingotingo.com/best-social-media-platforms/")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LAST_CANVA_FILE = "last_canva_link.txt"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content if content else "")


def send_telegram(message):
    if not TOKEN or not CHAT_ID:
        print("❌ Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
        r.raise_for_status()
        print("✅ تم إرسال الرسالة للتيليجرام")
    except Exception as e:
        print("⚠️ فشل إرسال رسالة:", e)


def find_real_get_here(page, base_domain_hint="bingotingo.com"):
    """يدور على زرار GET HERE اللي رابطه حقيقي (مش # ومش رجوع لنفس الموقع)."""
    links = page.query_selector_all("a")
    for link in links:
        try:
            text = (link.inner_text() or "").strip().lower()
        except Exception:
            continue
        if text != "get here":
            continue
        href = link.get_attribute("href")
        if href and href != "#" and base_domain_hint not in href:
            return href
    return None


def check_page():
    last_canva = read_file(LAST_CANVA_FILE)
    canva_url = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()

        print(f"🔍 فتح الصفحة الرئيسية: {URL}")
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")

        download_link = page.query_selector("a:has-text('Download')")
        if not download_link:
            print("❌ مفيش زر Download دلوقتي")
            browser.close()
            return

        download_href = download_link.get_attribute("href")
        if not download_href:
            print("❌ الزرار موجود بس href فارغ")
            browser.close()
            return

        print(f"➡️ فتح الصفحة الداخلية: {download_href}")
        page.goto(download_href, timeout=30000, wait_until="domcontentloaded")

        # محاولة أولى: يمكن الرابط الحقيقي يبقى ظاهر على طول
        canva_url = find_real_get_here(page)

        # لو لسه مفيش، دوس على الزرار اللي فيه fetchSecureLink بالتحديد
        if not canva_url:
            try:
                challenge_btn = page.query_selector("a[onclick*='fetchSecureLink']")
                if challenge_btn:
                    original_url = page.url
                    pages_before = len(context.pages)

                    try:
                        challenge_btn.click(timeout=5000)
                    except Exception as e:
                        print("⚠️ خطأ أثناء الضغط:", e)

                    page.wait_for_timeout(4000)

                    # 1) هل اتفتح تاب جديد؟
                    if len(context.pages) > pages_before:
                        new_page = context.pages[-1]
                        try:
                            new_page.wait_for_load_state(timeout=8000)
                        except Exception:
                            pass
                        popup_url = new_page.url
                        print(f"🆕 اتفتح تاب جديد برابط: {popup_url}")
                        if popup_url and popup_url != "about:blank":
                            canva_url = popup_url
                        new_page.close()

                    # 2) هل الصفحة الحالية اتنقلت؟
                    if not canva_url and page.url != original_url:
                        print(f"➡️ الصفحة الحالية اتغيرت لـ: {page.url}")
                        canva_url = page.url

                    # 3) هل الـ href بتاع نفس الزرار اتحدّث في مكانه؟
                    if not canva_url:
                        canva_url = find_real_get_here(page)
                    if not canva_url:
                        new_href = challenge_btn.get_attribute("href")
                        if new_href and new_href != "#":
                            canva_url = new_href
                else:
                    print("❌ مفيش زرار فيه fetchSecureLink")
            except Exception as e:
                print("⚠️ خطأ أثناء محاولة الضغط على زرار التحدي:", e)

        browser.close()

    if not canva_url:
        print("❌ لسه معرفناش نوصل للرابط الحقيقي بعد التحدي")
        print("---- 🔬 معلومات تشخيصية ----")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=UA, locale="en-US")
            page = context.new_page()
            page.goto(download_href, timeout=30000, wait_until="networkidle")
            page.wait_for_timeout(2000)

            all_links = page.query_selector_all("a")
            print(f"عدد الروابط في الصفحة: {len(all_links)}")
            for i, link in enumerate(all_links):
                try:
                    text = (link.inner_text() or "").strip()
                except Exception:
                    text = "?"
                href = link.get_attribute("href")
                onclick = link.get_attribute("onclick")
                print(f"  [{i}] text='{text}' href='{href}' onclick='{onclick}'")

            body_text = page.inner_text("body")
            if "aptcha" in body_text or "Captcha" in body_text:
                idx = body_text.find("aptcha")
                print("نص حوالين كلمة Captcha:")
                print(body_text[max(0, idx-100):idx+300])

            browser.close()
        return

    print(f"🔗 الرابط النهائي: {canva_url}")
    if canva_url != last_canva:
        send_telegram(f"🎨 الرابط من زر Get Here:\n{canva_url}")
        write_file(LAST_CANVA_FILE, canva_url)
    else:
        print("ℹ️ نفس الرابط القديم، مفيش تغيير")


if __name__ == "__main__":
    check_page()
