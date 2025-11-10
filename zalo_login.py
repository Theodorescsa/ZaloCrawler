import json
import time
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


ZALO_LOGIN_URL = "https://chat.zalo.me/"


class ZaloAPICapturer:
    def __init__(self, headless: bool = False):
        self.driver = None
        self.headless = headless
        self.setup_driver()

    # ================== SETUP & HOOK ==================

    def _build_hook_script(self) -> str:
        """
        Script JS sẽ được inject TỪ LÚC NEW DOCUMENT (trước khi trang Zalo chạy script của nó).
        Hook cả fetch và XMLHttpRequest.
        """
        return r"""
        (function() {
            // Tránh inject nhiều lần
            if (window.__zaloHookInstalled) {
                return;
            }
            window.__zaloHookInstalled = true;

            // Nơi lưu các lần gọi API login
            window.__zaloLoginInfoList = [];

            function saveLoginInfo(url, data) {
                try {
                    if (!url || typeof url !== 'string') return;
                    if (!url.includes('/api/login/getLoginInfo')) return;

                    const record = {
                        request_url: url,
                        response_data: data || null,
                        timestamp: Date.now()
                    };

                    console.log('🔍 [HOOK] Bắt được getLoginInfo:', record);
                    window.__zaloLoginInfoList.push(record);
                } catch (e) {
                    console.log('❌ [HOOK] Lỗi saveLoginInfo:', e);
                }
            }

            // ========== HOOK FETCH ==========
            try {
                const originalFetch = window.fetch;
                if (originalFetch) {
                    window.fetch = function(...args) {
                        const url = args[0];

                        return originalFetch.apply(this, args).then(response => {
                            try {
                                if (url && typeof url === 'string' && url.includes('/api/login/getLoginInfo')) {
                                    const cloned = response.clone();
                                    cloned.json()
                                        .then(data => {
                                            saveLoginInfo(url, data);
                                        })
                                        .catch(() => {});
                                }
                            } catch (e) {
                                console.log('❌ [HOOK] Lỗi xử lý fetch:', e);
                            }
                            return response;
                        });
                    };
                    console.log('✅ [HOOK] Đã hook fetch');
                }
            } catch (e) {
                console.log('❌ [HOOK] Fetch hook error:', e);
            }

            // ========== HOOK XHR ==========
            try {
                const originalOpen = XMLHttpRequest.prototype.open;
                const originalSend = XMLHttpRequest.prototype.send;

                XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
                    this.__zaloUrl = url;
                    return originalOpen.apply(this, arguments);
                };

                XMLHttpRequest.prototype.send = function(body) {
                    const xhr = this;
                    xhr.addEventListener('load', function() {
                        try {
                            if (xhr.__zaloUrl && xhr.__zaloUrl.includes('/api/login/getLoginInfo')) {
                                // cố gắng parse JSON
                                let data = null;
                                try {
                                    data = JSON.parse(xhr.responseText);
                                } catch (e) {}

                                saveLoginInfo(xhr.__zaloUrl, data);
                            }
                        } catch (e) {
                            console.log('❌ [HOOK] XHR load error:', e);
                        }
                    });

                    return originalSend.apply(this, arguments);
                };

                console.log('✅ [HOOK] Đã hook XMLHttpRequest');
            } catch (e) {
                console.log('❌ [HOOK] XHR hook error:', e);
            }

            console.log('✅ [HOOK] Script hook Zalo đã inject (new document)');
        })();
        """

    def setup_driver(self):
        """Thiết lập Chrome driver + inject hook từ lúc new document."""
        print("🚀 Đang khởi tạo Chrome driver...")

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/117.0.0.0 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)

        # Ẩn navigator.webdriver
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        # Inject hook TỪ LÚC NEW DOCUMENT (trước khi load Zalo)
        hook_script = self._build_hook_script()
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": hook_script}
        )

        print("✅ Chrome driver đã sẵn sàng & hook đã được cài đặt từ sớm")

    # ================== LOGIN FLOW ==================

    def login_manually(self) -> bool:
        """Mở Zalo & cho user đăng nhập thủ công."""
        print("🔐 Đang mở trang đăng nhập Zalo...")
        self.driver.get(ZALO_LOGIN_URL)

        # Chờ body để chắc là page đã load cơ bản
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        print("=" * 60)
        print("🤔 VUI LÒNG ĐĂNG NHẬP THỦ CÔNG")
        print("📝 Các bước:")
        print("   1. Nhập số điện thoại / mật khẩu hoặc quét QR")
        print("   2. Hoàn thành xác thực nếu có")
        print("   3. Chờ vào được giao diện chat")
        print("   4. QUAY LẠI TERMINAL VÀ NHẤN ENTER")
        print("=" * 60)

        input("⏰ Sau khi đăng nhập thành công, nhấn Enter để tiếp tục...")
        return True

    # ================== LẤY DATA HOOK ==================

    def _get_hooked_login_info_list(self):
        """Lấy list các record getLoginInfo đã bị hook."""
        try:
            data = self.driver.execute_script(
                "return window.__zaloLoginInfoList || [];"
            )
            return data or []
        except Exception:
            return []

    def wait_for_api_call(self, timeout: int = 30):
        """Chờ cho đến khi có ít nhất 1 call /api/login/getLoginInfo."""
        print(f"⏳ Đang chờ API getLoginInfo được gọi (tối đa {timeout}s)...")

        start_time = time.time()
        last_len = 0

        while time.time() - start_time < timeout:
            info_list = self._get_hooked_login_info_list()
            if info_list:
                if len(info_list) != last_len:
                    last_len = len(info_list)
                    print(f"✅ Đã bắt được {last_len} lần gọi getLoginInfo")
                # lấy record mới nhất
                return info_list[-1]

            elapsed = int(time.time() - start_time)
            print(f"⏰ Đã chờ {elapsed}s...", end="\r")
            time.sleep(1)

        print("\n❌ Không thấy API được gọi sau thời gian chờ")
        return None

    # ================== XỬ LÝ DATA ==================

    @staticmethod
    def extract_url_params(url: str):
        """Trích xuất zcid & zcid_ext từ URL."""
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)

            zcid = query_params.get('zcid', [None])[0]
            zcid_ext = query_params.get('zcid_ext', [None])[0]
            return zcid, zcid_ext
        except Exception:
            return None, None

    def extract_cookies(self):
        """Trích xuất cookies thành dict."""
        print("🍪 Đang trích xuất cookies...")
        cookies = self.driver.get_cookies()
        cookies_dict = {c["name"]: c["value"] for c in cookies}
        print(f"✅ Đã trích xuất {len(cookies_dict)} cookies")
        return cookies_dict

    def capture_login_info(self):
        """Flow chính: chờ API, parse dữ liệu, gom lại thành dict."""
        print("\n" + "=" * 50)
        print("🚀 BẮT ĐẦU CHẶN THÔNG TIN ĐĂNG NHẬP")
        print("=" * 50)

        api_data = self.wait_for_api_call(timeout=60)
        if not api_data:
            return None

        request_url = api_data.get("request_url", "") or ""
        response_data = api_data.get("response_data", {}) or {}

        zcid, zcid_ext = self.extract_url_params(request_url)
        if not zcid or not zcid_ext:
            print("❌ Không tìm thấy zcid hoặc zcid_ext trong URL")
            return None

        cookies = self.extract_cookies()
        encrypted_data = response_data.get("data")

        result = {
            "zcid": zcid,
            "zcid_ext": zcid_ext,
            "cookies": cookies,
            "api_response": response_data,
            "encrypted_data": encrypted_data,
            "request_url": request_url,
            "timestamp": time.time(),
        }

        print("\n" + "=" * 50)
        print("✅ CHẶN THÔNG TIN THÀNH CÔNG!")
        print("=" * 50)
        print(f"ZCID: {zcid}")
        print(f"ZCID_EXT: {zcid_ext}")
        if encrypted_data:
            print(f"Encrypted Data (preview): {str(encrypted_data)[:80]}...")
        else:
            print("Encrypted Data: Không có")
        print(f"API Error Code: {response_data.get('error_code', 'N/A')}")
        print(f"Số lượng cookies: {len(cookies)}")

        return result

    @staticmethod
    def save_to_file(data, filename: str = "zalo_api_data.json") -> bool:
        """Lưu dữ liệu vào file JSON."""
        if not data:
            print("❌ Không có dữ liệu để lưu")
            return False

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"💾 Đã lưu thông tin vào file: {filename}")
        return True

    def close(self):
        """Đóng trình duyệt."""
        if self.driver:
            self.driver.quit()
            print("🔚 Đã đóng trình duyệt")


def main():
    print("🤖 BOT CHẶN API ZALO - GETLOGININFO")
    print("=" * 50)

    capturer = ZaloAPICapturer(headless=False)

    try:
        if capturer.login_manually():
            api_data = capturer.capture_login_info()
            if api_data:
                capturer.save_to_file(api_data)
                print("\n🎉 HOÀN TẤT!")
                print("Thông tin API đã được lưu vào file 'zalo_api_data.json'")
            else:
                print("❌ Không thể lấy thông tin API")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("⏰ Nhấn Enter để đóng trình duyệt...")
        capturer.close()


if __name__ == "__main__":
    main()
