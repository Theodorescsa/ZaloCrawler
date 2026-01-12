# -*- coding: utf-8 -*-
import base64, json, hashlib, time, uuid
from urllib.parse import quote, unquote
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict
import os
from curl_cffi import requests as cffi_requests

# ====== PURE UTILS (KHÔNG DÙNG GLOBAL) ======
def _b64decode_padded(s: str) -> bytes:
    s = s.strip().replace(" ", "+")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)

def _b64encode_nopad(b: bytes) -> str:
    return base64.b64encode(b).decode().rstrip("=")

def _pkcs7_pad(b: bytes, block: int = 16) -> bytes:
    pad = block - (len(b) % block)
    return b + bytes([pad]) * pad

def _pkcs7_unpad(b: bytes) -> bytes:
    if not b:
        return b
    p = b[-1]
    if p < 1 or p > 16 or b[-p:] != bytes([p]) * p:
        raise ValueError("Bad PKCS7 padding")
    return b[:-p]


class ZaloClient:
    """
    Client không dùng biến global:
    - secret_key_b64
    - cookie_string
    - friend_domain
    - zpw_ver
    - zpw_type
    đều truyền qua __init__.
    """

    def __init__(
        self,
        secret_key_b64: str,
        cookie_string: str,
        friend_domain: str = "https://tt-friend-wpa.chat.zalo.me",
        chat_domain: str = "https://tt-chat2-wpa.chat.zalo.me",
        group_domain: str = "https://tt-group-wpa.chat.zalo.me",
        profile_domain: str = "https://tt-profile-wpa.chat.zalo.me", # <--- THÊM DÒNG NÀY
        zpw_ver: str = "676", # Update theo log của bạn
        zpw_type: str = "30",
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    ):
        self.secret_key_b64 = secret_key_b64
        self.cookie_string = cookie_string
        self.friend_domain = friend_domain.rstrip("/")
        self.chat_domain = chat_domain.rstrip("/")
        self.group_domain = group_domain.rstrip("/")
        self.profile_domain = profile_domain.rstrip("/") # <--- THÊM DÒNG NÀY
        self.zpw_ver = zpw_ver
        self.zpw_type = zpw_type
        self.user_agent = user_agent
        self._aes_key: Optional[bytes] = None
    def _normalize_phone(self, phone: str) -> str:
        """
        Chuẩn hóa SĐT về định dạng Zalo yêu cầu (84xxxxxxxxx).
        Loại bỏ ký tự lạ, đổi 0 đầu thành 84.
        """
        # 1. Chỉ giữ lại số (xóa dấu cách, dấu +, dấu -)
        clean_phone = "".join(filter(str.isdigit, phone))
        
        # 2. Xử lý đầu số
        if clean_phone.startswith("0"):
            return "84" + clean_phone[1:]
        
        # Trường hợp user copy paste cả 84 sẵn thì giữ nguyên
        return clean_phone
    # ---------- INTERNAL HELPERS ----------
    def _get(self, url: str, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
            # CẬP NHẬT: Thêm tham số proxies
            return requests.get(url, headers=self._headers(), params=params, timeout=30, proxies=proxies)

    def _post(self, url: str, data: Optional[str] = None, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        # CẬP NHẬT: Thêm tham số proxies
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return requests.post(url, headers=headers, data=data, params=params, timeout=30, proxies=proxies)
    def _get_aes_key(self) -> bytes:
        if self._aes_key is not None:
            return self._aes_key

        key = _b64decode_padded(self.secret_key_b64)
        # CryptoJS dùng raw key 16/24/32 bytes. Nếu độ dài ko đúng, sha256 cho 32b
        if len(key) not in (16, 24, 32):
            key = hashlib.sha256(key).digest()
        self._aes_key = key
        return key

    def encodeAES(self, plaintext: str) -> str:
        """CryptoJS AES-CBC(IV=0...0, PKCS7), output base64 (không padding '=')"""
        key = self._get_aes_key()
        iv = bytes(16)  # 16 zero bytes
        pt = plaintext.encode("utf-8")
        ct = AES.new(key, AES.MODE_CBC, iv=iv).encrypt(_pkcs7_pad(pt))
        return _b64encode_nopad(ct)

    def decodeAES(self, cipher_b64_or_url: str) -> str:
        """Giải mã ciphertext base64 (URL-encoded ok)"""
        try:
            cipher_b64_or_url = unquote(cipher_b64_or_url)
        except Exception:
            pass

        key = self._get_aes_key()
        iv = bytes(16)

        cipher = cipher_b64_or_url.strip().replace(" ", "+")
        cipher += "=" * (-len(cipher) % 4)
        ct = base64.b64decode(cipher)
        pt = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct)
        return _pkcs7_unpad(pt).decode("utf-8", "ignore")

    def _headers(self) -> Dict[str, str]:
        return {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self.user_agent,
            "Origin": "https://chat.zalo.me",
            "Referer": "https://chat.zalo.me/",
            "Cookie": self.cookie_string,
        }

    def _common_qs(self) -> str:
        return f"zpw_ver={self.zpw_ver}&zpw_type={self.zpw_type}"

    def _get(self, url: str, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        return requests.get(url, headers=self._headers(), params=params, timeout=30, proxies=proxies)
    # Cập nhật lại hàm _post để nhận tham số proxies
    def _post(self, url: str, data: Optional[str] = None, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        # Truyền proxies vào requests.post
        return requests.post(url, headers=headers, data=data, params=params, timeout=30, proxies=proxies)
    # ---------- PUBLIC API METHODS ----------

    def getUserByPhone(
        self,
        phone: str,
        reqSrc: Optional[str] = None,
        avatar_size: int = 240,
        language: str = "vi",
        imei: Optional[str] = None,
        proxies: Optional[Dict] = None # <--- Thêm tham số này
    ):
        if imei is None:
            imei = str(uuid.uuid4())

        payload = {
            "phone": phone,
            "avatar_size": avatar_size,
            "language": language,
            "imei": imei,
        }
        if reqSrc:
            payload["reqSrc"] = reqSrc

        data_str = json.dumps(payload, ensure_ascii=False)
        enc = self.encodeAES(data_str)
        
        url = f"{self.friend_domain}/api/friend/profile/get?{self._common_qs()}&params={quote(enc)}"
        
        # Truyền proxies vào đây
        resp = self._get(url, proxies=proxies)
        resp.raise_for_status()
        j = resp.json()

        if j.get("error_code") != 0:
            # Check lỗi rate limit cụ thể của Zalo (thường code -30, -366, hoặc text specific)
            if j.get("error_code") in [-366, -30]: 
                raise Exception(f"RATE_LIMITED: {j}")
            raise RuntimeError(f"API error: {j}")

        plaintext = self.decodeAES(j["data"])
        try:
            return json.loads(plaintext)
        except Exception:
            return {"raw": plaintext}
    def getMultiUsersByPhones(
        self,
        phones,
        avatar_size: int = 240,
        language: str = "vi",
    ):
        """
        Lấy thông tin nhiều người dùng bằng số điện thoại
        Args:
            phones: Danh sách số điện thoại (list of strings)
            avatar_size: Kích thước avatar (mặc định 240)
            language: Ngôn ngữ (mặc định "vi")
        """
        payload = {
            "phones": phones,
            "avatar_size": avatar_size,
            "language": language,
        }

        data_str = json.dumps(payload, ensure_ascii=False)
        enc = self.encodeAES(data_str)

        url = f"{self.friend_domain}/api/friend/profile/multiget?{self._common_qs()}&params={quote(enc)}"
        resp = self._get(url)
        resp.raise_for_status()
        j = resp.json()

        if j.get("error_code") != 0:
            raise RuntimeError(f"API error: {j}")

        plaintext = self.decodeAES(j["data"])
        try:
            return json.loads(plaintext)
        except Exception:
            return {"raw": plaintext}

    def getRecommendedFriendsV2(self, imei: Optional[str] = None):
        if imei is None:
            imei = str(uuid.uuid4())

        payload = {
            "imei": imei
        }
        
        data_str = json.dumps(payload, ensure_ascii=False)
        enc = self.encodeAES(data_str)
        
        url = f"{self.friend_domain}/api/friend/recommendsv2/list?{self._common_qs()}&params={quote(enc)}"
        
        resp = self._get(url)
        resp.raise_for_status()
        j = resp.json()

        if j.get("error_code") != 0:
            raise RuntimeError(f"API error: {j}")

        plaintext = self.decodeAES(j["data"])
        try:
            return json.loads(plaintext)
        except Exception:
            return {"raw": plaintext}

    def getProfilesV2(
        self,
        friend_pversion_map: list,
        phonebook_version: int = 0,
        avatar_size: int = 120,
        language: str = "vi",
        show_online_status: int = 1,
        imei: Optional[str] = None,
        proxies: Optional[Dict] = None
    ):
        """
        Lấy thông tin profile bạn bè (V2) - API này thường dùng để check update profile.
        
        Args:
            friend_pversion_map: List các string dạng "uid_version". 
                                 Ví dụ: ["7538827358818806826_0"] (0 là lấy mới nhất).
            phonebook_version: Version danh bạ (timestamp), có thể để 0 hoặc timestamp hiện tại.
            avatar_size: Kích thước ảnh đại diện (default 120 theo log).
            proxies: Dictionary proxy nếu có.
        """
        if imei is None:
            imei = str(uuid.uuid4())

        payload = {
            "phonebook_version": phonebook_version,
            "friend_pversion_map": friend_pversion_map,
            "avatar_size": avatar_size,
            "language": language,
            "show_online_status": show_online_status,
            "imei": imei
        }

        # 1. Mã hóa payload
        data_str = json.dumps(payload, ensure_ascii=False)
        enc = self.encodeAES(data_str)

        # 2. Tạo body dạng x-www-form-urlencoded
        # Lưu ý: POST request của Zalo thường gửi body là chuỗi params=...
        body = f"params={quote(enc)}"

        # 3. Tạo URL (Sử dụng profile_domain)
        url = f"{self.profile_domain}/api/social/friend/getprofiles/v2?{self._common_qs()}"

        # 4. Gửi request
        # Hàm _post đã set sẵn Content-Type: application/x-www-form-urlencoded
        resp = self._post(url, data=body, proxies=proxies)
        resp.raise_for_status()
        
        j = resp.json()

        if j.get("error_code") != 0:
            if j.get("error_code") in [-366, -30]: 
                 raise Exception(f"RATE_LIMITED: {j}")
            raise RuntimeError(f"API error: {j}")

        # 5. Giải mã response
        if "data" in j:
            plaintext = self.decodeAES(j["data"])
            try:
                return json.loads(plaintext)
            except Exception:
                return {"raw": plaintext}
        return j

    def sendSmartMessage(self, identifier: str, message: str):
        target_uid = identifier

        # --- BƯỚC 1: Xử lý Identifier ---
        # Kiểm tra nếu là SĐT (chuỗi số < 15 ký tự)
        is_phone = len(identifier) < 15 and identifier.isdigit()
        
        if is_phone:
            # Tối ưu 1: Chuẩn hóa ngay lập tức (09x -> 849x) -> Bỏ qua được request lỗi
            phone = self._normalize_phone(identifier)
            print(f"[INFO] Input là SĐT. Đã chuẩn hóa: {identifier} -> {phone}")
            
            try:
                # Chỉ gọi 1 lần duy nhất với số đã chuẩn
                info_obj = self.getUserByPhone(phone)
                data = info_obj.get("data", {})
                
                # Extract UID (hỗ trợ cả uid và userId)
                extracted_uid = data.get("uid") or data.get("userId")
                
                if extracted_uid:
                    target_uid = extracted_uid
                    name = data.get("display_name") or data.get("zaloName") or "Unknown"
                    print(f"[SUCCESS] Tìm thấy UID: {target_uid} ({name})")
                else:
                    return {
                        "error_code": -1, 
                        "error_message": f"Không tìm thấy Zalo cho SĐT {phone}. (Lỗi: {info_obj.get('error_message')})"
                    }

            except Exception as e:
                return {"error_code": -2, "error_message": f"Lỗi mạng khi tra cứu SĐT: {e}"}

        # --- BƯỚC 2: Gửi tin nhắn ---
        # Nếu logic trên chạy đúng, target_uid giờ là UID xịn.
        print(f"[INFO] Đang gửi tin nhắn tới UID: {target_uid}...")
        return self.sendTextMessage(to_uid=target_uid, message=message)
    def wait_for_qr_login_with_cookie_fixed(self, proxies: Optional[Dict] = None):
        """
        Phiên bản Hardcode Cookie: Bỏ qua warm-up tự động để tránh bị chặn IP/Fingerprint.
        """
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            print("Chưa cài curl_cffi")
            return None

        # ==============================================================================
        # [QUAN TRỌNG] DÁN COOKIE TỪ TRÌNH DUYỆT THẬT VÀO DÒNG DƯỚI ĐÂY
        # ==============================================================================
        MANUAL_COOKIE = "zpdid=4HR_arpqgpGQ4PERMF37DHeKb9rTyC8q; ozi=2000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbwrAxraqyOtpIUfVUMIX7VCj6bz9865zatrQNyD3ar.1; _ga_1J0YGQPT22=GS1.1.1743267239.1.1.1743267278.21.0.0; _gcl_au=1.1.1210773121.1762247361; _fbp=fb.1.1762247361146.837283859710473447; __zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayOt3EUhlQGGHEMDP6YkfP75f8rcQUtDG.1; zoaw_sek=QkLN.1968800208.2.8wLFSLG-2NI4lr01L3u9T5G-2NHKFWbqLGMDA3q-2NG; zoaw_type=0; _ga_NVN38N77J3=GS2.2.s1767670840$o4$g1$t1767670845$j55$l0$h0; _ga_WSPJQT0ZH1=GS2.1.s1767670858$o3$g1$t1767670880$j38$l0$h0; _ga_E63JS7SPBL=GS2.1.s1767670834$o5$g1$t1767670883$j11$l0$h0; _gid=GA1.2.1733340641.1767856264; _zlang=vn; app.event.zalo.me=616744305790528006; zpsid=Fpsv.355636788.160.doADeKtx4B5vRIAaGViGiJY8Oe9upYQ2UymeYLQr58fJvhSMJBvpxYJx4B4; _ga_907M127EPP=GS2.1.s1767944044$o7$g1$t1767944083$j21$l0$h0; _ga_YT9TMXZYV9=GS2.1.s1767949537$o11$g0$t1767949537$j60$l0$h0; _gat=1; _ga_RYD7END4JE=GS2.2.s1767964530$o54$g1$t1767964531$j59$l0$h0; _ga_YS1V643LGV=GS2.1.s1767964530$o56$g0$t1767964531$j59$l0$h0; zlogin_session=kW4JGLyjCnIxFnDDLXTbH-Tj1q1U5cT5xMyVLmHIQLscBXDO54rsMAqk6raYVG; _ga=GA1.2.759643980.1743071453; _ga_3EM8ZPYYN3=GS2.2.s1767964534$o49$g0$t1767964534$j60$l0$h0"  # <--- DÁN VÀO ĐÂY (GIỮ NGUYÊN DẤU NGOẶC KÉP)
        # ==============================================================================

        if len(MANUAL_COOKIE) < 20 or "zpsid" not in MANUAL_COOKIE:
            print("\n[LỖI] Bạn chưa dán Cookie hoặc Cookie thiếu 'zpsid'.")
            print("Vui lòng lấy Cookie từ F12 -> Network trên trình duyệt thật.")
            return None

        print("\n[LOGIN] --- BẮT ĐẦU (CHẾ ĐỘ THỦ CÔNG) ---")
        
        if os.path.exists("zalo_qr.png"):
            os.remove("zalo_qr.png")

        # 1. IMEI
        if os.path.exists("imei.txt"):
            with open("imei.txt", "r") as f:
                my_imei = f.read().strip()
        else:
            my_imei = str(uuid.uuid4())
            with open("imei.txt", "w") as f:
                f.write(my_imei)

        REAL_VER = self.zpw_ver

        # 2. KHỞI TẠO SESSION
        # Dùng chrome120 là đủ vì ta đã có cookie xịn
        session = cffi_requests.Session(impersonate="chrome120")
        
        base_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://id.zalo.me/account?continue=https%3A%2F%2Fchat.zalo.me%2F",
            "Origin": "https://id.zalo.me",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.6,en;q=0.5",
            # Inject Cookie thủ công vào Header
            "Cookie": MANUAL_COOKIE,
            # Các header giả lập trình duyệt
            "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=1, i"
        }
        session.headers.update(base_headers)

        print("[INIT] Đã nạp Cookie thủ công. Bỏ qua bước Warm-up.")

        # --- BƯỚC 1: VERIFY CLIENT (Bắt buộc để hiện Popup) ---
        print(f"[INIT] Xác thực thiết bị...")
        try:
            verify_payload = {
                "type": "device",
                "imei": my_imei,
                "computer_name": "Chrome_Windows",
                "continue": self.chat_domain + "/",
                "v": REAL_VER
            }
            # Request này sẽ dùng cookie thủ công để báo với server rằng "Session này là hợp lệ"
            session.post("https://id.zalo.me/account/verify-client", data=verify_payload, proxies=proxies)
        except Exception as e:
            print(f"[WARN] Verify lỗi (có thể bỏ qua): {e}")

        # --- BƯỚC 2: ĐỒNG BỘ SESSION (JR) ---
        print(f"[INIT] Đồng bộ UserInfo...")
        try:
            headers_jr = base_headers.copy()
            headers_jr["Referer"] = "https://chat.zalo.me/"
            headers_jr["Origin"] = "https://chat.zalo.me"
            
            session.get(
                "https://jr.chat.zalo.me/jr/userinfo", 
                headers=headers_jr,
                proxies=proxies
            )
        except Exception:
            pass

        # --- BƯỚC 3: TẠO QR ---
        print("[ACTION] Đang tạo mã QR...")
        try:
            ts = int(time.time() * 1000)
            # Đảm bảo header quay về id.zalo.me
            session.headers.update(base_headers)
            
            resp = session.post(
                f"https://id.zalo.me/account/authen/qr/generate?ts={ts}",
                data={"continue": self.chat_domain + "/", "v": REAL_VER, "imei": my_imei},
                proxies=proxies
            )
            data_gen = resp.json()
            
            if data_gen.get("error_code") != 0:
                print(f"[ERROR] Server chặn: {data_gen}")
                return False

            qr_code_id = data_gen["data"]["code"]
            qr_image_b64 = data_gen["data"]["image"]

            with open("zalo_qr.png", "wb") as f:
                f.write(base64.b64decode(qr_image_b64.split(",")[1]))
            
            print(f"[ACTION] QR ID: {qr_code_id}")
            print(">>> QUÉT MÃ NGAY (Mở Zalo trên điện thoại -> Quét QR) <<<")

        except Exception as e:
            print(f"[ERROR] Lỗi tạo QR: {e}")
            return False

        # --- BƯỚC 4: CHỜ QUÉT ---
        print("[WAIT] Đang chờ quét...", end="", flush=True)
        url_scan = "https://id.zalo.me/account/authen/qr/waiting-scan"
        url_confirm = "https://id.zalo.me/account/authen/qr/waiting-confirm"
        
        step = 1
        
        while True:
            try:
                if step == 1:
                    resp = session.post(url_scan, data={
                        "code": qr_code_id, 
                        "continue": self.chat_domain + "/", 
                        "v": REAL_VER
                    }, proxies=proxies)
                    j = resp.json()
                    
                    if j.get("error_code") == 0:
                        print("\n[SUCCESS] Đã quét! Đang đợi xác nhận...")
                        step = 2
                    elif j.get("error_code") == -1004:
                         print("\n[FAIL] QR hết hạn.")
                         return False

                elif step == 2:
                    resp = session.post(url_confirm, data={
                        "code": qr_code_id, 
                        "gToken": "", 
                        "gAction": "CONFIRM_QR", 
                        "continue": self.chat_domain + "/", 
                        "v": REAL_VER
                    }, proxies=proxies)
                    j = resp.json()
                    
                    if j.get("error_code") == 0:
                        print("\n[SUCCESS] Đăng nhập thành công!")
                        break
                    elif j.get("error_code") == -1004:
                        print("\n[FAIL] Hết hạn/Từ chối.")
                        return False
            except Exception:
                time.sleep(1)
                continue

            print(".", end="", flush=True)
            time.sleep(2)

        # --- KẾT THÚC ---
        # Cập nhật lại cookie_string từ session (bao gồm cookie mới nếu có)
        cookies = session.cookies.get_dict()
        # Ưu tiên lấy từ session, nếu không có thì dùng lại cookie thủ công
        if not cookies:
             self.cookie_string = MANUAL_COOKIE
        else:
             self.cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        print(f"[INFO] Final Cookie Length: {len(self.cookie_string)}")
        return {"status": "ok"}

    def wait_for_qr_login(self, proxies: Optional[Dict] = None):
        print("\n[LOGIN] --- BẮT ĐẦU (SAFARI MODE) ---")
        
        if os.path.exists("zalo_qr.png"):
            os.remove("zalo_qr.png")

        # 1. IMEI
        if os.path.exists("imei.txt"):
            with open("imei.txt", "r") as f:
                my_imei = f.read().strip()
        else:
            my_imei = str(uuid.uuid4())
            with open("imei.txt", "w") as f:
                f.write(my_imei)

        REAL_VER = self.zpw_ver

        # ============================================================
        # CẤU HÌNH SAFARI (Login Zalo mượt hơn Chrome)
        # ============================================================
        # Safari 15.3 thường có sẵn trong curl_cffi bản cũ lẫn mới
        
        # 1. Đổi sang Chrome Impersonate (Phổ biến và ít bị lỗi fingerprint hơn Safari trên Win)
        try:
            # Dùng chrome110 hoặc chrome120 nếu lib hỗ trợ
            session = cffi_requests.Session(impersonate="chrome120")
        except:
            session = cffi_requests.Session(impersonate="chrome110")

        # 2. Header chuẩn cho Chrome (Bỏ header Safari cũ đi)
        base_headers = {
            # curl_cffi tự set User-Agent khớp với bản Chrome impersonate, 
            # ĐỪNG set cứng User-Agent Safari ở đây sẽ bị lộ bot ngay.
            "Referer": "https://id.zalo.me/",
            "Origin": "https://id.zalo.me",
            "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            "sec-ch-ua-platform": '"Windows"', # Vì bạn đang chạy trên Win
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        session.headers.update(base_headers)

        # --- BƯỚC 1: WARM-UP CHIẾN THUẬT MỚI ---
        # Flow chuẩn trình duyệt:
        # 1. Vào chat.zalo.me (để lấy cookie tracking ban đầu)
        # 2. Redirect sang id.zalo.me (lúc này mới sinh zpsid)
        
        print("[INIT] Đang warm-up (Flow mới)...")
        has_zpsid = False
        
        try:
            # Request 1: Giả vờ vào trang chat trước
            session.get("https://chat.zalo.me/", proxies=proxies, timeout=10)
            
            # Request 2: Gọi trang login chính (QUAN TRỌNG: Đây là nơi zpsid được set)
            # Không cần gọi api logininfo vội, chỉ cần GET trang html là đủ
            login_url = f"https://id.zalo.me/account?continue={quote(self.chat_domain + '/')}&v={self.zpw_ver}"
            
            resp = session.get(login_url, proxies=proxies, timeout=15)
            
            # Debug: In thử xem có bị redirect sang trang captcha không
            if "captcha" in resp.url:
                print("🛑 CẢNH BÁO: Đang bị dính Captcha/WAF chặn IP!")
            
            # Kiểm tra cookie
            cookies = session.cookies.get_dict()
            if "zpsid" in cookies:
                print(f"[OK] Đã có zpsid: {cookies['zpsid'][:10]}...")
                has_zpsid = True
            else:
                # Nếu chưa có, thử gọi nhẹ logininfo (như code cũ của bạn)
                print("[RETRY] Chưa thấy zpsid, thử kích hoạt logininfo...")
                session.post(
                    "https://id.zalo.me/account/logininfo",
                    data={"continue": self.chat_domain + "/", "v": self.zpw_ver},
                    proxies=proxies
                )
                
                cookies = session.cookies.get_dict()
                if "zpsid" in cookies:
                    print(f"[OK] Đã có zpsid sau khi post logininfo.")
                    has_zpsid = True

        except Exception as e:
            print(f"[ERROR] Lỗi Warmup: {e}")

        # --- BƯỚC 2: VERIFY CLIENT ---
        print(f"[INIT] Xác thực thiết bị...")
        try:
            verify_payload = {
                "type": "device",
                "imei": my_imei,
                "computer_name": "Mac_Safari",
                "continue": self.chat_domain + "/",
                "v": REAL_VER
            }
            session.post("https://id.zalo.me/account/verify-client", data=verify_payload, proxies=proxies)
        except Exception:
            pass

        # --- BƯỚC 3: GỌI USERINFO ---
        print(f"[INIT] Đồng bộ UserInfo...")
        try:
            headers_jr = base_headers.copy()
            headers_jr["Referer"] = "https://chat.zalo.me/"
            headers_jr["Origin"] = "https://chat.zalo.me"
            # Giả lập Safari trên Mac
            headers_jr["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15"
            
            session.get(
                "https://jr.chat.zalo.me/jr/userinfo", 
                headers=headers_jr,
                proxies=proxies
            )
        except Exception:
            pass

        # --- BƯỚC 4: TẠO QR ---
        print("[ACTION] Đang tạo mã QR...")
        try:
            ts = int(time.time() * 1000)
            session.headers.update(base_headers)
            
            resp = session.post(
                f"https://id.zalo.me/account/authen/qr/generate?ts={ts}",
                data={"continue": self.chat_domain + "/", "v": REAL_VER, "imei": my_imei},
                proxies=proxies
            )
            data_gen = resp.json()
            
            if data_gen.get("error_code") != 0:
                print(f"[ERROR] Server chặn: {data_gen}")
                return False

            qr_code_id = data_gen["data"]["code"]
            qr_image_b64 = data_gen["data"]["image"]

            with open("zalo_qr.png", "wb") as f:
                f.write(base64.b64decode(qr_image_b64.split(",")[1]))
            
            print(f"[ACTION] QR ID: {qr_code_id}")
            print(">>> QUÉT MÃ NGAY <<<")

        except Exception as e:
            print(f"[ERROR] Lỗi tạo QR: {e}")
            return False

        # --- BƯỚC 5: CHỜ QUÉT ---
        print("[WAIT] Đang chờ quét...", end="", flush=True)
        url_scan = "https://id.zalo.me/account/authen/qr/waiting-scan"
        url_confirm = "https://id.zalo.me/account/authen/qr/waiting-confirm"
        
        step = 1
        
        while True:
            try:
                if step == 1:
                    resp = session.post(url_scan, data={
                        "code": qr_code_id, 
                        "continue": self.chat_domain + "/", 
                        "v": REAL_VER
                    }, proxies=proxies)
                    j = resp.json()
                    
                    if j.get("error_code") == 0:
                        print("\n[SUCCESS] Đã quét! Đang đợi xác nhận...")
                        step = 2
                    elif j.get("error_code") == -1004:
                         print("\n[FAIL] QR hết hạn.")
                         return False

                elif step == 2:
                    resp = session.post(url_confirm, data={
                        "code": qr_code_id, 
                        "gToken": "", 
                        "gAction": "CONFIRM_QR", 
                        "continue": self.chat_domain + "/", 
                        "v": REAL_VER
                    }, proxies=proxies)
                    j = resp.json()
                    
                    if j.get("error_code") == 0:
                        print("\n[SUCCESS] Đăng nhập thành công!")
                        break
                    elif j.get("error_code") == -1004:
                        print("\n[FAIL] Hết hạn/Từ chối.")
                        return False
            except Exception:
                time.sleep(1)
                continue

            print(".", end="", flush=True)
            time.sleep(2)

        # --- KẾT THÚC ---
        cookies = session.cookies.get_dict()
        self.cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        print(f"[INFO] Cookie Length: {len(self.cookie_string)}")
        return {"status": "ok"}