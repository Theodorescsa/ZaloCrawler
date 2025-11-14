from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

# 👉 NHỚ đổi IP:PORT của profile MoreLogin tại đây
DEBUG_ADDRESS = "127.0.0.1:55005"   # ví dụ

def open_morelogin_browser(debug_address: str):
    print(f"🔗 Đang attach vào MoreLogin browser tại {debug_address}...")

    options = Options()
    options.debugger_address = debug_address

    driver = webdriver.Chrome(options=options)

    # Ẩn navigator.webdriver (optional)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    print("✅ Đã attach thành công!")
    print("🔍 Browser title:", driver.title)

    return driver


if __name__ == "__main__":
    driver = open_morelogin_browser(DEBUG_ADDRESS)

    print("\n🔥 Giữ browser mở để bạn tự làm gì tùy thích...")
    print("⏳ Script sẽ chạy chờ 5 phút. Bạn đóng cửa sổ cũng được.")

    try:
        time.sleep(300)  # giữ 5 phút
    except KeyboardInterrupt:
        pass

    print("👋 Kết thúc session test!")
