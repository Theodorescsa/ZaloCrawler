from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time

DEBUG_ADDRESS = "127.0.0.1:41073"  # port bạn lấy được từ MoreLogin
CHROMEDRIVER_PATH = r"E:\NCS\ChromeDriver\chromedriver-win64\chromedriver.exe"  # <-- đường dẫn driver 140

def open_morelogin_browser(debug_address: str):
    print(f"🔗 Đang attach vào MoreLogin browser tại {debug_address}...")

    options = Options()
    options.debugger_address = debug_address

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)

    # optional: ẩn webdriver flag
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    print("✅ Đã attach thành công!")
    print("🔍 Title hiện tại:", driver.title)
    return driver


if __name__ == "__main__":
    driver = open_morelogin_browser(DEBUG_ADDRESS)

    print("⏳ Giữ browser mở 5 phút cho bạn test...")
    try:
        time.sleep(300)
    except KeyboardInterrupt:
        pass

    driver.quit()
