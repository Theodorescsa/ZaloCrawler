import time
import json
import base64
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# -------- CONFIG --------
BASE_URL = "https://id.zalo.me"
GENERATE_PATH = "/account/authen/qr/generate"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://id.zalo.me",
    "Referer": "https://id.zalo.me/account?continue=https%3A%2F%2Fchat.zalo.me%2F",
}
PAYLOAD = {"continue": "https://chat.zalo.me/", "v": "5.6.1"}

# How long to wait before collecting cookies.
# You can increase if you need time to login / interact in the opened browser.
WAIT_BEFORE_CAPTURE = 8
# ------------------------

def save_base64_image(b64_str: str, out_path: Path) -> bool:
    m = re.match(r"data:image/(png|jpeg|jpg);base64,(.+)$", b64_str, flags=re.I)
    if m:
        b64_str = m.group(2)
    try:
        data = base64.b64decode(b64_str)
        out_path.write_bytes(data)
        return True
    except Exception as e:
        print("[!] Error decoding base64:", e)
        return False

def find_qr_candidate_in_json(j: dict):
    def search(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = k.lower()
                if isinstance(v, str) and any(x in lk for x in ("qr", "qrcode", "qr_image", "qrimage", "image")):
                    return v
                r = search(v)
                if r:
                    return r
        elif isinstance(obj, list):
            for it in obj:
                r = search(it)
                if r:
                    return r
        return None
    return search(j)

def open_chrome_and_get_session(wait_seconds: int = WAIT_BEFORE_CAPTURE):
    """
    Opens Chrome (Selenium-managed, visible). You can interact manually.
    After wait_seconds (or pressing Enter), the function extracts cookies and returns a requests.Session
    """
    opts = Options()
    opts.add_argument("--start-maximized")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    try:
        driver.get("https://id.zalo.me/account?continue=https%3A%2F%2Fchat.zalo.me%2F")
        print(f"[i] Chrome opened by Selenium. You can interact now (login/scan/accept).")
        print(f"[i] Waiting {wait_seconds}s before capturing cookies. If you need more time, press Ctrl+C and re-run with larger WAIT_BEFORE_CAPTURE.")
        time.sleep(wait_seconds)
        cookies = driver.get_cookies()
        session = requests.Session()
        session.headers.update(HEADERS)
        for c in cookies:
            name = c.get("name")
            value = c.get("value")
            domain = c.get("domain", None)
            # requests accepts cookies without domain, but setting domain helps sometimes
            session.cookies.set(name, value, domain=domain)
        print(f"[+] Captured {len(cookies)} cookies from Selenium browser.")
        return session
    finally:
        try:
            driver.quit()
        except Exception:
            pass

# def post_generate_and_handle(session: requests.Session):
#     url = urljoin(BASE_URL, GENERATE_PATH)
#     print("[*] POST ->", url)
#     r = session.post(url, data=PAYLOAD, timeout=20)
#     print("[*] HTTP", r.status_code)
#     try:
#         j = r.json()
#     except Exception:
#         print("[!] Response not JSON (truncated):")
#         print(r.text[:2000])
#         return
#     print("[i] JSON keys:", list(j.keys()) if isinstance(j, dict) else "not-dict")
#     # Try find QR
#     candidate = find_qr_candidate_in_json(j)
#     saved = False
#     if candidate:
#         out_dir = Path("zalo_qr_out")
#         out_dir.mkdir(exist_ok=True)
#         out_file = out_dir / "qrcode.png"
#         if candidate.startswith("data:image/") or (len(candidate) > 200 and re.fullmatch(r"[A-Za-z0-9+/=\s]+", candidate.strip())):
#             if save_base64_image(candidate, out_file):
#                 print("[+] Saved QR image to", out_file)
#                 saved = True
#         elif candidate.startswith("http"):
#             try:
#                 rr = session.get(candidate, timeout=20)
#                 if rr.status_code == 200:
#                     out_file.write_bytes(rr.content)
#                     print("[+] Downloaded QR to", out_file)
#                     saved = True
#             except Exception as e:
#                 print("[-] Failed to download candidate URL:", e)

#     if not saved:
#         print("[i] Could not auto-save QR. Dumping truncated JSON for manual inspection:")
#         print(json.dumps(j, ensure_ascii=False)[:4000])

def main():
    print("[*] Starting Selenium-based cookie capture (no user-data-dir).")
    session = open_chrome_and_get_session(wait_seconds=WAIT_BEFORE_CAPTURE)
    if not session:
        print("[-] Could not get session from browser.")
        return
    # post_generate_and_handle(session)
    print("[*] Done.")

if __name__ == "__main__":
    main()
