# -*- coding: utf-8 -*-
import base64, json, hashlib, time, uuid
from urllib.parse import quote, unquote
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict
import os

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
    def wait_for_qr_login(self, proxies: Optional[Dict] = None):
        try:
            from curl_cffi import requests as cffi_requests
        except ImportError:
            print("Chưa cài curl_cffi")
            return None

        print("\n[LOGIN] --- BẮT ĐẦU (FIX NO POPUP) ---")
        
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

        # ==========================================
        # CẤU HÌNH QUAN TRỌNG THEO LOG BROWSER
        # ==========================================
        # Update Version mới nhất từ Log của bạn
        REAL_VER = "5.6.1" 
        
        # Dùng Chrome 124 cho mới (gần với 142)
        session = cffi_requests.Session(impersonate="chrome124")
        
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://id.zalo.me/account?continue=https%3A%2F%2Fchat.zalo.me%2F",
            "Origin": "https://id.zalo.me",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.6,en;q=0.5",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        })

        # --- BƯỚC 1: WARM-UP LẤY COOKIE (BẮT BUỘC PHẢI CÓ ZPSID/ZPDID) ---
        print("[INIT] Đang khởi tạo Session để lấy Cookie...")
        try:
            # Gọi 2 lần để đảm bảo cookie được set đầy đủ
            session.get("https://id.zalo.me/account", proxies=proxies, timeout=10)
            time.sleep(1)
            # Gọi lại đúng URL có tham số để trigger cookie zpsid
            url_page = f"https://id.zalo.me/account?continue={quote(self.chat_domain + '/')}&v={REAL_VER}"
            resp_init = session.get(url_page, proxies=proxies, timeout=10)
            
            cookies = session.cookies.get_dict()
            # Debug Cookie
            print(f"[DEBUG] Cookies hiện có: {list(cookies.keys())}")
            
            if "zpsid" not in cookies and "zpdid" not in cookies:
                print("[WARNING] Vẫn chưa lấy được zpsid/zpdid. Thử ép cookie giả lập...")
                # Fallback: Nếu mạng chặn cookie, ta có thể thử fake 1 cái zpdid (nhưng tốt nhất là để tự nhiên)
                # session.cookies.set("zpdid", "CAKE_ZPDID_FAKE") 
            
        except Exception as e:
            print(f"[ERROR] Lỗi warm-up: {e}")

        # --- BƯỚC 2: VERIFY CLIENT ---
        # Bước này giúp Server biết phiên này là tin cậy => Mới cho phép đẩy Popup
        print(f"[INIT] Xác thực thiết bị...")
        try:
            verify_payload = {
                "type": "device",
                "imei": my_imei,
                "computer_name": "Chrome_Windows",
                "continue": self.chat_domain + "/",
                "v": REAL_VER  # Quan trọng: Phải khớp version
            }
            session.post("https://id.zalo.me/account/verify-client", data=verify_payload, proxies=proxies)
            time.sleep(0.5)
        except Exception as e:
            print(f"[WARN] Verify lỗi: {e}")

        # --- BƯỚC 3: TẠO QR ---
        print("[ACTION] Đang tạo mã QR...")
        try:
            # Thêm tham số ts (timestamp) để tránh cache
            ts = int(time.time() * 1000)
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
            print(">>> QUÉT MÃ NGAY (Nhớ tắt App Zalo điện thoại mở lại trước khi quét) <<<")

        except Exception as e:
            print(f"[ERROR] Lỗi tạo QR: {e}")
            return False

        # --- BƯỚC 4: CHỜ QUÉT (WAITING SCAN) ---
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
                        print("\n[SUCCESS] Đã quét! Đang đợi bạn bấm 'Đăng nhập' trên điện thoại...")
                        # Khi server trả về 0 ở đây, nó cũng trigger tín hiệu xuống đt
                        # Nếu đt không hiện, là do request generate bên trên thiếu cookie session
                        step = 2
                    elif j.get("error_code") == -1004:
                         print("\n[FAIL] QR hết hạn.")
                         return False

                elif step == 2:
                    # Polling chờ Confirm
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
                        print("\n[FAIL] Hết hạn hoặc bạn đã bấm Từ chối.")
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