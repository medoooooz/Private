import os
import requests
from playwright.sync_api import sync_playwright

# === إعدادات ===
URL = os.getenv("WEBSITE_URL", "https://bingotingo.com/best-social-media-platforms/")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LAST_LINK_FILE = "last_canva_link.txt"

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


def check_page():
    last_link = read_file(LAST_LINK_FILE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=UA, locale="en-US")
        page = context.new_page()

        print(f"🔍 فحص الصفحة الرئيسية: {URL}")
        page.goto(URL, timeout=30000, wait_until="domcontentloaded")

        download_link = page.query_selector("a:has-text('Download')")
        if not download_link:
            print("❌ مفيش زر Download دلوقتي")
            browser.close()
            return

        current_link = download_link.get_attribute("href")
        browser.close()

    if not current_link:
        print("❌ الزرار موجود بس href فارغ")
        return

    print(f"🔗 الرابط الحالي: {current_link}")

    if current_link != last_link:
        send_telegram(f"🔔 اتغيّر رابط الـ Download:\n{current_link}")
        write_file(LAST_LINK_FILE, current_link)
    else:
        print("ℹ️ نفس الرابط القديم، مفيش تغيير")


if __name__ == "__main__":
    check_page()
