import json
import os
import time
import subprocess
import socket
from typing import List, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# ----------------------------
# CONFIG: chỉnh cho phù hợp
# ----------------------------
CHROME_PATH   = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"E:\NCS\Userdata"       # thư mục user data (chứa các Profile)
PROFILE_NAME  = "Profile 5"              # ví dụ: "Profile 5", "Default"
REMOTE_PORT   = 9222                     # khác với port bạn dùng ở crawler để khỏi đụng nhau

# Các origin sẽ vào để lấy storage
ORIGINS = [
    "https://www.facebook.com/",
    "https://m.facebook.com/",
    "https://web.facebook.com/",
]

# Domain cookie cần lấy (substring match, không quá khắt khe)
ALLOWED_COOKIE_DOMAINS = [
    ".facebook.com",
    "facebook.com",
    "m.facebook.com",
    "web.facebook.com",
]

# File output
OUT_COOKIES_PATH       = r"cookies.json"
OUT_LOCALSTORAGE_PATH  = r"localstorage.json"
OUT_SESSIONSTORAGE_PATH= r"sessionstorage.json"

# ----------------------------
# Utils
# ----------------------------
def _wait_port(host: str, port: int, timeout: float = 15.0, poll: float = 0.1) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except Exception:
            time.sleep(poll)
    return False


def start_driver() -> webdriver.Chrome:
    # Mở đúng profile thật bằng remote debugging
    args = [
        CHROME_PATH,
        f'--remote-debugging-port={REMOTE_PORT}',
        f'--user-data-dir={USER_DATA_DIR}',
        f'--profile-directory={PROFILE_NAME}',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-extensions',
        '--disable-background-networking',
        '--disable-popup-blocking',
        '--disable-default-apps',
        '--disable-infobars',
        '--window-size=1280,900',
        # KHÔNG dùng --headless khi export storage: 1 số site cần non-headless để init storage
    ]
    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not _wait_port('127.0.0.1', REMOTE_PORT, timeout=20):
        raise RuntimeError(f"Chrome remote debugging port {REMOTE_PORT} not available.")

    options = Options()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{REMOTE_PORT}")
    driver = webdriver.Chrome(options=options)
    return driver

def filter_cookies(all_cookies: List[Dict[str, Any]],
                   allow_domains: List[str]) -> List[Dict[str, Any]]:
    out = []
    for ck in all_cookies:
        domain = ck.get("domain") or ""
        if any(d in domain for d in allow_domains):
            # Chuẩn hóa một số field để tương thích Network.setCookie
            item = {
                "name": ck.get("name"),
                "value": ck.get("value"),
                "domain": domain,
                "path": ck.get("path", "/"),
                "secure": bool(ck.get("secure", False)),
                "httpOnly": bool(ck.get("httpOnly", False)),
            }
            # SameSite: CDP trả về "Strict"/"Lax"/"None" hoặc None
            ss = ck.get("sameSite") or ck.get("same_site")
            if ss in ("Strict", "Lax", "None"):
                item["sameSite"] = ss
            # expires: giây epoch hoặc None
            expires = ck.get("expires")
            if isinstance(expires, (int, float)) and expires > 0:
                item["expires"] = expires
            out.append(item)
    return out

def dump_storage(driver: webdriver.Chrome, origins: List[str]):
    """
    Trả về:
      local_map: dict origin -> {key:value}
      session_map: dict origin -> {key:value}
    """
    local_map: Dict[str, Dict[str, str]] = {}
    session_map: Dict[str, Dict[str, str]] = {}

    for url in origins:
        try:
            driver.get(url)
            time.sleep(0.8)
            # localStorage
            ls = driver.execute_script("""
                const o = {};
                try {
                    for (let i=0; i<localStorage.length; i++){
                        const k = localStorage.key(i);
                        o[k] = localStorage.getItem(k);
                    }
                } catch(e) {}
                return o;
            """)
            # sessionStorage
            ss = driver.execute_script("""
                const o = {};
                try {
                    for (let i=0; i<sessionStorage.length; i++){
                        const k = sessionStorage.key(i);
                        o[k] = sessionStorage.getItem(k);
                    }
                } catch(e) {}
                return o;
            """)
            local_map[url] = ls or {}
            session_map[url] = ss or {}
            print(f"[STORAGE] {url} -> local={len(local_map[url])} keys, session={len(session_map[url])} keys")
        except Exception as e:
            print(f"[WARN] storage dump failed for {url}: {e}")

    return local_map, session_map

def smart_merge_storage(storage_by_origin: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """
    Một số key (AB test, device info) bị lặp giữa origins → gộp đơn giản:
    - ưu tiên origin chính https://www.facebook.com/
    - các origin khác chỉ add key chưa có
    """
    merged: Dict[str, str] = {}
    priority = [
        "https://www.facebook.com/",
        "https://web.facebook.com/",
        "https://m.facebook.com/",
    ]
    # build ordered origins list
    ordered = [o for o in priority if o in storage_by_origin] + [o for o in storage_by_origin if o not in priority]
    for origin in ordered:
        for k, v in (storage_by_origin.get(origin) or {}).items():
            if k not in merged:
                merged[k] = v
    return merged

def main():
    driver = start_driver()

    # # 1) Lấy tất cả cookies từ profile qua CDP (gồm HttpOnly)
    # driver.execute_cdp_cmd("Network.enable", {})
    # res = driver.execute_cdp_cmd("Network.getAllCookies", {})
    # all_cookies = res.get("cookies", []) if isinstance(res, dict) else []
    # fb_cookies = filter_cookies(all_cookies, ALLOWED_COOKIE_DOMAINS)
    # print(f"[COOKIES] total={len(all_cookies)}, selected={len(fb_cookies)}")

    # with open(OUT_COOKIES_PATH, "w", encoding="utf-8") as f:
    #     json.dump(fb_cookies, f, ensure_ascii=False, indent=2)
    # print(f"[WRITE] {OUT_COOKIES_PATH}")

    # # 2) Dump localStorage & sessionStorage theo origin
    # local_map, session_map = dump_storage(driver, ORIGINS)

    # # 3) Gộp lại thành 1 dict (ưu tiên www) cho tiện dùng lại
    # local_merged = smart_merge_storage(local_map)
    # session_merged = smart_merge_storage(session_map)

    # with open(OUT_LOCALSTORAGE_PATH, "w", encoding="utf-8") as f:
    #     json.dump(local_merged, f, ensure_ascii=False, indent=2)
    # print(f"[WRITE] {OUT_LOCALSTORAGE_PATH} (total keys={len(local_merged)})")

    # with open(OUT_SESSIONSTORAGE_PATH, "w", encoding="utf-8") as f:
    #     json.dump(session_merged, f, ensure_ascii=False, indent=2)
    # print(f"[WRITE] {OUT_SESSIONSTORAGE_PATH} (total keys={len(session_merged)})")

    # # Done
    # driver.quit()
    # print("[DONE] Exported cookies + local/session storage from real profile.")

if __name__ == "__main__":
    main()