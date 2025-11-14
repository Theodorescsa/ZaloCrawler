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
USER_DATA_DIR = r"E:\NCS\Userdata"  
PROFILE_NAME  = "Profile 5"           
REMOTE_PORT   = 9222

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


def main():
    driver = start_driver()
if __name__ == "__main__":
    main()