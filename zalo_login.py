import json
import time
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException

from solve_captcha import solve_zalo_captcha

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
    def _switch_to_captcha_context(self) -> bool:
        """
        Switch vào context (default hoặc iframe) chứa captcha.
        Return True nếu tìm được challenge-container, False nếu không.
        """
        self.driver.switch_to.default_content()

        def _has_captcha_in_current():
            try:
                self.driver.find_element(
                    By.CSS_SELECTOR,
                    "div.challenge-container"
                )
                return True
            except NoSuchElementException:
                return False

        # 1) Thử ngay ở default_content
        if _has_captcha_in_current():
            return True

        # 2) Thử lần lượt các iframe
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        for frame in iframes:
            try:
                self.driver.switch_to.default_content()
                self.driver.switch_to.frame(frame)
                if _has_captcha_in_current():
                    print("✅ Đã tìm thấy captcha trong một iframe")
                    return True
            except Exception:
                continue

        # 3) Không có -> về lại default_content và trả False
        self.driver.switch_to.default_content()
        print("⚠️ Không tìm thấy challenge-container trong bất kỳ context nào")
        return False
    def click_captcha_tiles(self, solved_result: str):
        """
        Click vào các ô captcha theo kết quả giải (ví dụ: '1,2,8')
        """
        try:
            print(f"🖱️ Đang click vào các ô captcha: {solved_result}")

            # Parse kết quả
            tiles_to_click = [
                int(x.strip())
                for x in str(solved_result).split(",")
                if x.strip()
            ]
            print(f"📋 Danh sách ô cần click: {tiles_to_click}")

            # Switch vào context chứa captcha
            if not self._switch_to_captcha_context():
                print("❌ Không tìm thấy context chứa captcha")
                return False

            wait = WebDriverWait(self.driver, 10)

            # DÙNG SELECTOR ỔN ĐỊNH, KHÔNG DÙNG CLASS HASHED
            table = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div.challenge-container table")
                )
            )

            tiles = table.find_elements(By.TAG_NAME, "td")
            print(f"🔍 Tìm thấy {len(tiles)} ô captcha")

            if len(tiles) == 0:
                print("❌ Không tìm thấy ô nào trong bảng captcha")
                return False

            # Click từng ô
            for tile_number in tiles_to_click:
                if 1 <= tile_number <= len(tiles):
                    tile_index = tile_number - 1
                    tile_el = tiles[tile_index]

                    print(f"👉 Đang click ô số {tile_number} (index {tile_index})")

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});",
                        tile_el
                    )
                    time.sleep(0.3)

                    # Click vào div bên trong td cho chắc cú
                    try:
                        inner_div = tile_el.find_element(By.TAG_NAME, "div")
                    except Exception:
                        inner_div = tile_el

                    self.driver.execute_script("arguments[0].click();", inner_div)

                    print(f"✅ Đã click ô {tile_number}")
                    time.sleep(0.7)
                else:
                    print(f"❌ Số ô {tile_number} vượt ngoài phạm vi (1-{len(tiles)})")

            print("🎯 Đã click xong tất cả các ô captcha")

            # Sau khi xong phải click nút Xác thực trong cùng context luôn
            self._click_verify_button()

            # Về lại default_content cho an toàn
            self.driver.switch_to.default_content()

            return True

        except Exception as e:
            print(f"❌ Lỗi khi click captcha tiles: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def _click_verify_button(self):
        """
        Click nút 'Xác thực' sau khi chọn xong các ô captcha.
        """
        try:
            print("🔍 Đang tìm nút 'Xác thực'...")

            # Đảm bảo đang ở đúng context captcha
            if not self._switch_to_captcha_context():
                print("⚠️ Không tìm được context captcha khi click nút 'Xác thực'")
                return False

            wait = WebDriverWait(self.driver, 10)

            verify_btn = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[contains(@class,'challenge-container')]"
                    "//div[contains(@class,'z_36Na4oyq__e141')]"
                ))
            )

            self.driver.execute_script("arguments[0].click();", verify_btn)
            print("✅ Đã click nút 'Xác thực'")
            time.sleep(3)

            # Về lại default_content
            self.driver.switch_to.default_content()
            return True

        except TimeoutException:
            print("⚠️ Không tìm thấy nút 'Xác thực', có thể captcha auto submit.")
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False
        except Exception as e:
            print(f"❌ Lỗi khi click nút xác thực: {e}")
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def get_captcha_info(self) -> dict:
        """
        Tìm thông tin captcha (câu hỏi + URL ảnh) nếu có.
        Có xử lý trường hợp captcha nằm trong iframe.
        """
        info = {
            'question': None,
            'image_url': None,
            'exists': False
        }

        try:
            wait = WebDriverWait(self.driver, 10)

            # 1) Luôn về default_content trước
            self.driver.switch_to.default_content()

            # 2) Thử tìm trực tiếp ngoài cùng trước
            def _find_in_current_context():
                try:
                    question_el = self.driver.find_element(
                        By.XPATH,
                        # tìm theo container + text "Chọn tất cả hình ảnh có"
                        "//div[contains(@class, 'challenge-container')]"
                        "//div[contains(text(), 'Chọn tất cả hình ảnh có')]"
                    )
                    img_el = self.driver.find_element(
                        By.XPATH,
                        "//div[contains(@class, 'challenge-container')]//img"
                    )
                    return question_el, img_el
                except Exception:
                    return None, None

            q_el, img_el = _find_in_current_context()

            # 3) Nếu chưa thấy, thử đi qua từng iframe
            if not q_el or not img_el:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for frame in iframes:
                    try:
                        self.driver.switch_to.default_content()
                        self.driver.switch_to.frame(frame)
                        q_el, img_el = _find_in_current_context()
                        if q_el and img_el:
                            break
                    except Exception:
                        continue

            # Sau khi thử xong, nếu vẫn không có → coi như không tồn tại
            if not q_el or not img_el:
                self.driver.switch_to.default_content()
                return info

            # 4) Lấy text câu hỏi + src ảnh
            question = q_el.text.strip()
            image_url = img_el.get_attribute("src")

            # Về lại default_content
            self.driver.switch_to.default_content()

            info['question'] = question
            info['image_url'] = image_url
            info['exists'] = True

            print(f"🎯 Captcha detected: {question} | {image_url}")
            return info

        except Exception as e:
            print(f"❌ Lỗi khi lấy thông tin captcha: {e}")
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            return info


    def find_to_login_with_account(self):
        """Click vào menu 'Đăng nhập với mật khẩu' ở màn QR login."""
        print("🔍 Đang tìm nút 'Đăng nhập với mật khẩu' ở màn QR...")
        wait = WebDriverWait(self.driver, 20)

        try:
            # 1) Nút 3 gạch (dropdown)
            dropdown_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.zdropdown button"))
            )
            dropdown_btn.click()

            # 2) Option 'Đăng nhập với mật khẩu' trong dropdown
            password_option = wait.until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//div[contains(@class,'zdropdown-container')]"
                    "//span[contains(normalize-space(text()), 'Đăng nhập với mật khẩu')]"
                ))
            )
            password_option.click()
            print("✅ Đã chuyển sang form đăng nhập bằng mật khẩu.")
        except TimeoutException:
            print("⚠️ Không tìm được menu 'Đăng nhập với mật khẩu'.")
            print("   Có thể Zalo đang hiển thị sẵn form mật khẩu hoặc giao diện đã đổi.")
    def login_with_password(self, phone: str, password: str) -> bool:
        """
        Mở chat.zalo.me, chọn 'Đăng nhập với mật khẩu',
        tự động điền SĐT + mật khẩu và bấm nút Đăng nhập.
        Trả về thông tin captcha nếu xuất hiện.
        """
        print("🔐 Đang mở trang đăng nhập Zalo (password mode)...")
        self.driver.get(ZALO_LOGIN_URL)

        wait = WebDriverWait(self.driver, 20)

        # Chờ body để chắc ăn trang đã load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # B1: Chuyển từ QR sang form mật khẩu (nếu cần)
        try:
            self.find_to_login_with_account()
        except Exception as e:
            print(f"⚠️ Lỗi khi chuyển sang form mật khẩu: {e}")

        # B2: Chờ form hiện ra
        try:
            phone_input = wait.until(
                EC.visibility_of_element_located((By.ID, "input-phone"))
            )
            password_input = wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, ".form-signin input[type='password']"))
            )
        except TimeoutException:
            print("❌ Không tìm thấy form đăng nhập (input SĐT / mật khẩu).")
            return False

        # B3: Điền thông tin
        print("✏️ Đang điền SĐT và mật khẩu...")
        phone_input.clear()
        phone_input.send_keys(phone)

        password_input.clear()
        password_input.send_keys(password)

        # B4: Chờ nút 'Đăng nhập với mật khẩu' hết disabled
        def _login_btn_ready(driver):
            try:
                btn = driver.find_element(
                    By.CSS_SELECTOR,
                    ".form-signin .btn.btn--m.block.first"
                )
                classes = (btn.get_attribute("class") or "").lower()
                # Nếu class không còn 'disabled' và element enable → ok
                return "disabled" not in classes and btn.is_enabled()
            except Exception:
                return False

        try:
            wait.until(_login_btn_ready)
            login_btn = self.driver.find_element(
                By.CSS_SELECTOR,
                ".form-signin .btn.btn--m.block.first"
            )
            login_btn.click()
            print("✅ Đã click nút 'Đăng nhập với mật khẩu'.")
        except TimeoutException:
            print("❌ Nút đăng nhập vẫn bị disabled, kiểm tra lại SĐT/mật khẩu/logic validate.")
            return False

        # B5: Kiểm tra captcha sau khi click login
        print("🔍 Đang kiểm tra captcha...")
        time.sleep(3)  # Chờ một chút để captcha load nếu có
        
        captcha_info = self.get_captcha_info()
        if captcha_info['exists']:
            print(f"🎯 Đã phát hiện captcha!")
            print(f"   Câu hỏi: {captcha_info['question']}")
            print(f"   URL ảnh: {captcha_info['image_url']}")
            # Có thể xử lý captcha ở đây hoặc trả về thông tin
            return captcha_info

        # B6: (Optional) Chờ vào được giao diện chat
        try:
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[role='main'], .conversation-list, .sidebar")
                )
            )
            print("🎉 Đã login thành công (đã thấy giao diện chat).")
        except TimeoutException:
            print("⚠️ Không detect được giao diện chat, nhưng request login đã được gửi.")
            # Kiểm tra lại captcha (có thể captcha xuất hiện muộn)
            captcha_info = self.get_captcha_info()
            if captcha_info['exists']:
                print(f"🎯 Đã phát hiện captcha (xuất hiện muộn)!")
                print(f"   Câu hỏi: {captcha_info['question']}")
                print(f"   URL ảnh: {captcha_info['image_url']}")
                return captcha_info

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
    PHONE = "0354235270"
    PASSWORD = "@Dinhthai2004-"

    try:
        info_captcha_result = capturer.login_with_password(PHONE, PASSWORD)
        if not info_captcha_result:
            print("❌ Lỗi khi đăng nhập")
            return
        
        print("info_captcha_result:", info_captcha_result)
        
        solved_captcha_result = solve_zalo_captcha(
            api_key="6faef718e1c982aa9a263efb748c95e7",
            image_base64_or_url=info_captcha_result["image_url"],
            instructions=info_captcha_result["question"],
            click_mode="zalo2",   # hoặc "zalo"
            poll_interval=5,
            timeout=120
        )
        # solved_captcha_result = "1,2,3,4,5,6,7,8,9"
        print("Kết quả giải captcha:", solved_captcha_result)
        
        # THÊM PHẦN NÀY: Click vào các ô captcha
        if solved_captcha_result:
            print("🖱️ Đang thực hiện click captcha...")
            click_success = capturer.click_captcha_tiles(solved_captcha_result)
            
            if click_success:
                print("✅ Đã xử lý captcha thành công")
                # Chờ một lúc để trang xử lý
                time.sleep(5)
            else:
                print("❌ Lỗi khi xử lý captcha")
                return
        
        # Tiếp tục lấy thông tin login
        data = capturer.capture_login_info()
        capturer.save_to_file(data)
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("⏰ Nhấn Enter để đóng trình duyệt...")
        capturer.close()

if __name__ == "__main__":
    main()
