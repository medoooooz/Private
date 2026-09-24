import os
import sys
import requests
from bs4 import BeautifulSoup

# === إعدادات ===
URL = os.getenv("WEBSITE_URL", "https://bingotingo.com/best-social-media-platforms/")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

LAST_CANVA_FILE = "last_canva_link.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# --- helpers ---
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

# --- فحص الصفحة ---
def check_page():
    last_canva = read_file(LAST_CANVA_FILE)

    try:
        print(f"🔍 فحص الصفحة الرئيسية: {URL}")
        resp = requests.get(URL, timeout=15, headers=HEADERS)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # --- البحث عن زر Download ---
        download_elem = None
        for a in soup.find_all("a", href=True):
            if a.text and "Download" in a.text:
                download_elem = a
                break

        if not download_elem:
            print("❌ مفيش زر Download دلوقتي")
            return

        download_url = download_elem.get("href")
        if not download_url:
            print("❌ الزرار موجود بس href فارغ")
            return

        # --- فتح الصفحة الداخلية ---
        inner_resp = requests.get(download_url, timeout=15, headers=HEADERS)
        inner_resp.raise_for_status()
        inner_soup = BeautifulSoup(inner_resp.text, "html.parser")

        # --- البحث عن زر GET HERE ---
        get_here_elem = None
        for a in inner_soup.find_all("a", href=True):
            if a.text and a.text.strip().lower() == "get here":
                get_here_elem = a
                break

        if get_here_elem:
            canva_url = get_here_elem.get("href")
            print(f"🔗 رابط Canva الموجود في الزر: {canva_url}")

            # --- إرسال الرابط إذا حصل تغيير ---
            if canva_url != last_canva:
                send_telegram(f"🎨 الرابط من زر Get Here:\n{canva_url}")
                write_file(LAST_CANVA_FILE, canva_url)
            else:
                print("ℹ️ نفس الرابط القديم، مفيش تغيير")
        else:
            print("❌ مفيش زر Get Here جوّه الصفحة الداخلية")

    except requests.RequestException as e:
        print("⚠️ خطأ في الشبكة:", e)
    except Exception as e:
        print("⚠️ خطأ:", e)


if __name__ == "__main__":
    check_page()
