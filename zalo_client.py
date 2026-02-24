# -*- coding: utf-8 -*-
import base64, json, hashlib, time, uuid
from urllib.parse import quote, unquote
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict
import os
from curl_cffi import requests
from zalo_param_cipher import ZaloParamCipher
from zalo_utils import _b64decode_padded, _b64encode_nopad, _pkcs7_pad, _pkcs7_unpad
class ZaloClient:
    def __init__(
        self,
        secret_key_b64: str,
        cookie_string: str,
        friend_domain: str = "https://tt-friend-wpa.chat.zalo.me",
        chat_domain: str = "https://tt-chat2-wpa.chat.zalo.me",
        group_domain: str = "https://tt-group-wpa.chat.zalo.me",
        profile_domain: str = "https://tt-profile-wpa.chat.zalo.me",
        zpw_ver: str = "676",
        zpw_type: str = "30",
        # User Agent phải khớp với bản impersonate chrome120
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ):
        self.secret_key_b64 = secret_key_b64
        self.cookie_string = cookie_string
        self.friend_domain = friend_domain.rstrip("/")
        self.chat_domain = chat_domain.rstrip("/")
        self.group_domain = group_domain.rstrip("/")
        self.profile_domain = profile_domain.rstrip("/")
        self.zpw_ver = zpw_ver
        self.zpw_type = zpw_type
        self.user_agent = user_agent
        self._aes_key: Optional[bytes] = None
        
        # [FIX] Dùng curl_cffi Session thay vì requests Session
        self.session = requests.Session(impersonate="chrome120")
        
        # Nạp cookie nếu có sẵn
        if self.cookie_string:
            self._load_cookies_to_session()

    def _load_cookies_to_session(self):
        """Helper để nạp cookie string vào cffi session"""
        if not self.cookie_string: return
        for pair in self.cookie_string.split(";"):
            if "=" in pair:
                try:
                    k, v = pair.strip().split("=", 1)
                    self.session.cookies.set(k, v, domain=".zalo.me")
                except: pass
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
    def _headers(self) -> Dict[str, str]:
        # [FIX] Bỏ Cookie cứng ở đây đi, để Session tự quản lý Cookie
        return {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self.user_agent,
            "Origin": "https://chat.zalo.me",
            "Referer": "https://chat.zalo.me/",
            # "Cookie": self.cookie_string, # <--- COMMENT DÒNG NÀY LẠI
        }

    def _get(self, url: str, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        headers = self._headers()
        if "Cookie" in headers: del headers["Cookie"] # Để session tự quản lý
        return self.session.get(url, headers=headers, params=params, timeout=30, proxies=proxies)

    def _post(self, url: str, data: Optional[str] = None, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        if "Cookie" in headers: del headers["Cookie"]
        return self.session.post(url, headers=headers, data=data, params=params, timeout=30, proxies=proxies)
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

    # def _headers(self) -> Dict[str, str]:
    #     return {
    #         "Accept": "application/json, text/plain, */*",
    #         "User-Agent": self.user_agent,
    #         "Origin": "https://chat.zalo.me",
    #         "Referer": "https://chat.zalo.me/",
    #         "Cookie": self.cookie_string,
    #     }

    def _common_qs(self) -> str:
        return f"zpw_ver={self.zpw_ver}&zpw_type={self.zpw_type}"

    def _get(self, url: str, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        headers = self._headers()
        # ✅ KHÔNG xóa Cookie nữa, để session tự quản lý
        return self.session.get(url, headers=headers, params=params, timeout=30, proxies=proxies)

    def _post(self, url: str, data: Optional[str] = None, params: Optional[Dict] = None, proxies: Optional[Dict] = None):
        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        # ✅ KHÔNG xóa Cookie
        return self.session.post(url, headers=headers, data=data, params=params, timeout=30, proxies=proxies)
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
        print(f"[DEBUG] Status Code: {resp.status_code}")
        print(f"[DEBUG] URL: {resp.url}")
        print(f"[DEBUG] Content-Type: {resp.headers.get('Content-Type', '')}")
        
        # In thử 500 ký tự đầu tiên xem nó là JSON hay HTML lỗi
        print(f"[DEBUG] Raw Body (first 500 chars): {resp.text[:500]}")

        # Kiểm tra nếu status code không phải 200 thì dừng luôn để xem lỗi
        if resp.status_code != 200:
            print("[ERROR] Request failed, not trying to parse JSON.")
            return {"error": "HttpError", "status": resp.status_code, "body": resp.text}
            
        try:
            j = resp.json()
        except Exception as e:
            print(f"[CRITICAL] Lỗi parse JSON: {e}")
            # Ghi lại toàn bộ response để phân tích
            with open("error_response.html", "w", encoding="utf-8") as f:
                f.write(resp.text)
            print("[INFO] Đã lưu response lỗi vào file error_response.html")
            return {"error": "JsonParseError", "raw": resp.text}
        if j.get("error_code") != 0:
            # Check lỗi rate limit cụ thể của Zalo (thường code -30, -366, hoặc text specific)
            if j.get("error_code") in [-366, -30]: 
                raise Exception(f"RATE_LIMITED: {j}")
            raise RuntimeError(f"API error: {j}")

        plaintext = self.decodeAES(j["data"])
        print('plaintext',plaintext)
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
    def sendTextMessage(
        self, 
        to_uid: str, 
        message: str, 
        imei: Optional[str] = None, 
        proxies: Optional[Dict] = None
    ):
        """
        Gửi tin nhắn văn bản cá nhân (Chat 1-1).
        Dựa trên JS: path=/api/message/sms, domainType=CHAT
        """
        if imei is None:
            imei = str(uuid.uuid4())

        # clientId thường là timestamp (milliseconds) để định danh tin nhắn phía client
        client_id = str(int(time.time() * 1000))

        payload = {
            "toid": to_uid,
            "message": message,
            "clientId": client_id,
            "imei": imei,
            "ttl": 0,          # Time to live (mặc định 0)
            "zsource": 101,    # Source 101 thường là Zalo Web/PC
            "is_force": 0,     # Mặc định
        }

        # 1. Mã hóa Payload
        data_str = json.dumps(payload, ensure_ascii=False)
        enc = self.encodeAES(data_str)

        # 2. Tạo body (x-www-form-urlencoded)
        body = f"params={quote(enc)}"

        # 3. Tạo URL
        # Sử dụng chat_domain thay vì profile_domain hay friend_domain
        url = f"{self.chat_domain}/api/message/sms?{self._common_qs()}"

        # 4. Gửi request
        resp = self._post(url, data=body, proxies=proxies)
        resp.raise_for_status()
        j = resp.json()
        print(f"[DEBUG] Status Code: {resp.status_code}")
        print(f"[DEBUG] Response: {j}")
        # 5. Xử lý lỗi
        if j.get("error_code") != 0:
            if j.get("error_code") in [-366, -30]:
                raise Exception(f"RATE_LIMITED: {j}")
            # Một số trường hợp gửi tin nhắn trả về data null nhưng error_code 0 là thành công
            raise RuntimeError(f"API error: {j}")

        # 6. Return kết quả
        # Thường API send message trả về { "error_code": 0, "data": { "msgId": "..." } }
        # Nếu data bị mã hóa thì giải mã, còn không thì trả về luôn
        if "data" in j and isinstance(j["data"], str):
            plaintext = self.decodeAES(j["data"])
            try:
                return json.loads(plaintext)
            except Exception:
                return {"raw": plaintext, "msg": "Decoded but not JSON"}
        
        return j
    def sendSmartMessage(self, identifier: str, message: str):
        """
        Gửi tin nhắn thông minh:
        1. Nếu là SĐT -> Gọi getUserByPhone để lấy UID.
        2. Dùng UID -> Gọi getProfilesV2 để xác thực và lấy thông tin chi tiết (giả lập hành vi thật).
        3. Gọi sendTextMessage để gửi tin.
        """
        target_uid = identifier
        user_profile_data = None

        # --- BƯỚC 1: Xử lý Identifier (SĐT -> UID) ---
        # Kiểm tra nếu là SĐT (chuỗi số < 15 ký tự và không phải là UID dài)
        # Lưu ý: UID của Zalo hiện nay thường dài khoảng 18-19 ký tự số, SĐT thì khoảng 10-12 số.
        is_looking_like_phone = len(identifier) <= 12 and identifier.isdigit()
        
        if is_looking_like_phone:
            phone = self._normalize_phone(identifier)
            print(f"[STEP 1] Input là SĐT. Đã chuẩn hóa: {identifier} -> {phone}")
            
            try:
                # Gọi API getUserByPhone
                info_obj = self.getUserByPhone(phone)
                
                # Check lỗi API
                if info_obj.get("error_code") != 0:
                    return {
                        "error_code": info_obj.get("error_code"), 
                        "error_message": f"Lỗi tra cứu SĐT: {info_obj.get('error_message')}"
                    }

                data = info_obj.get("data", {})
                
                # Lấy UID (ưu tiên uid, fallback sang userId)
                extracted_uid = data.get("uid") or data.get("userId")
                
                if extracted_uid:
                    target_uid = extracted_uid
                    name = data.get("display_name") or data.get("zalo_name") or "Unknown"
                    print(f"[STEP 1 OK] Tìm thấy UID từ SĐT: {target_uid} ({name})")
                else:
                    return {
                        "error_code": -1, 
                        "error_message": f"API trả về thành công nhưng không tìm thấy UID cho SĐT {phone}."
                    }

            except Exception as e:
                return {"error_code": -2, "error_message": f"Exception tại bước getUserByPhone: {e}"}
        else:
            print(f"[STEP 1] Input được coi là UID: {target_uid}")

        # --- BƯỚC 2: Gọi getProfilesV2 (Verify User & Mimic Real Behavior) ---
        # Zalo Web luôn gọi cái này trước khi chat để lấy avatar, tên hiển thị, check chặn...
        print(f"[STEP 2] Đang xác thực profile cho UID: {target_uid}...")
        
        try:
            # Map request: UID_0 (0 nghĩa là lấy version mới nhất)
            friend_map = [f"{target_uid}_0"]
            
            profile_resp = self.getProfilesV2(friend_pversion_map=friend_map)
            
            if profile_resp.get("error_code") != 0:
                 print(f"[WARNING] Không lấy được profile (Code {profile_resp.get('error_code')}). Vẫn cố gắng gửi tin nhắn...")
            else:
                # Kiểm tra xem có data của user này trong response không
                changed_profiles = profile_resp.get("data", {}).get("changed_profiles", {})
                if target_uid in changed_profiles:
                    user_profile_data = changed_profiles[target_uid]
                    # Lấy tên hiển thị chính xác nhất tại thời điểm hiện tại
                    final_name = user_profile_data.get("zaloName") or user_profile_data.get("displayName")
                    print(f"[STEP 2 OK] Đã verify profile: {final_name} | GlobalID: {user_profile_data.get('globalId')}")
                else:
                    print(f"[WARNING] API Profile OK nhưng không thấy data của UID {target_uid}. Có thể UID sai hoặc bị chặn.")

        except Exception as e:
            print(f"[WARNING] Lỗi tại bước getProfilesV2 (không chặn luồng gửi tin): {e}")

        # --- BƯỚC 3: Gửi tin nhắn (sendTextMessage) ---
        print(f"[STEP 3] Đang gửi tin nhắn tới UID: {target_uid}...")
        
        # Gọi hàm gửi tin nhắn gốc
        result = self.sendTextMessage(to_uid=target_uid, message=message)
        
        # (Optional) Đính kèm thêm thông tin profile đã lấy được vào kết quả trả về để tiện debug/log
        if result.get("error_code") == 0 and user_profile_data:
            result["_debug_profile_info"] = {
                "name": user_profile_data.get("zaloName"),
                "global_id": user_profile_data.get("globalId")
            }
            
        return result
    def wait_for_qr_login(self, proxies: Optional[Dict] = None):        
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

        # Session setup
        try:
            session = requests.Session(impersonate="chrome110")
        except:
            session = requests.Session(impersonate="chrome110")

        base_headers = {
            "Referer": "https://id.zalo.me/",
            "Origin": "https://id.zalo.me",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        session.headers.update(base_headers)

        # --- WARM-UP ---
        print("[INIT] Đang warm-up...")
        try:
            session.get("https://chat.zalo.me/", proxies=proxies, timeout=10)
            
            login_url = f"https://id.zalo.me/account?continue={quote(self.chat_domain + '/')}&v={self.zpw_ver}"
            resp = session.get(login_url, proxies=proxies, timeout=15)
            
            cookies = session.cookies.get_dict()
            if "zpsid" not in cookies:
                print("[RETRY] Kích hoạt logininfo...")
                session.post(
                    "https://id.zalo.me/account/logininfo",
                    data={"continue": self.chat_domain + "/", "v": self.zpw_ver},
                    proxies=proxies
                )
        except Exception as e:
            print(f"[WARN] Warmup error: {e}")

        # --- VERIFY CLIENT ---
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
        except:
            pass

        # --- USERINFO ---
        print(f"[INIT] Đồng bộ UserInfo...")
        try:
            headers_jr = base_headers.copy()
            headers_jr["Referer"] = "https://chat.zalo.me/"
            headers_jr["Origin"] = "https://chat.zalo.me"
            headers_jr["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15"
            session.get("https://jr.chat.zalo.me/jr/userinfo", headers=headers_jr, proxies=proxies)
        except:
            pass

        # --- TẠO QR ---
        print("[ACTION] Đang tạo mã QR...")
        try:
            ts = int(time.time() * 1000)
            resp = session.post(
                f"https://id.zalo.me/account/authen/qr/generate?ts={ts}",
                data={"continue": self.chat_domain + "/", "v": REAL_VER, "imei": my_imei},
                proxies=proxies
            )
            data_gen = resp.json()
            
            if data_gen.get("error_code") != 0:
                print(f"[ERROR] {data_gen}")
                return False

            qr_code_id = data_gen["data"]["code"]
            qr_image_b64 = data_gen["data"]["image"]

            with open("zalo_qr.png", "wb") as f:
                f.write(base64.b64decode(qr_image_b64.split(",")[1]))
            
            print(f"[ACTION] QR ID: {qr_code_id}")
            print(">>> QUÉT MÃ NGAY <<<")
        except Exception as e:
            print(f"[ERROR] {e}")
            return False

        # --- CHỜ QUÉT ---
        print("[WAIT] Đang chờ quét...", end="", flush=True)
        url_scan = "https://id.zalo.me/account/authen/qr/waiting-scan"
        url_confirm = "https://id.zalo.me/account/authen/qr/waiting-confirm"
        
        step = 1
        confirm_response = None
        
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
                        print("\n[SUCCESS] Đã quét! Đợi xác nhận...")
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
                    }, proxies=proxies, allow_redirects=False)  # ✅ KHÔNG auto redirect
                    
                    j = resp.json()
                    
                    if j.get("error_code") == 0:
                        print("\n[SUCCESS] QR confirmed!")
                        confirm_response = j
                        break
                    elif j.get("error_code") == -1004:
                        print("\n[FAIL] Hết hạn/Từ chối.")
                        return False
            except Exception as e:
                print(f"\n[ERROR] {e}")
                time.sleep(1)
                continue

            print(".", end="", flush=True)
            time.sleep(2)

        # ✅ ===== BƯỚC QUAN TRỌNG: FOLLOW REDIRECT ĐỂ LẤY COOKIE =====
        print("[REDIRECT] Đang follow redirect để lấy session cookies...")
        
        try:
            # 1. Kiểm tra xem response có redirect URL không
            redirect_url = None
            
            if confirm_response and "data" in confirm_response:
                # Một số response trả về redirect URL trong data
                redirect_url = confirm_response["data"].get("redirect_url") or confirm_response["data"].get("url")
            
            # 2. Nếu không có explicit redirect URL, gọi continue URL
            if not redirect_url:
                redirect_url = self.chat_domain + "/"
            
            print(f"[REDIRECT] Accessing: {redirect_url}")
            
            # 3. Gọi redirect URL (cho phép auto-redirect)
            # Header phải giống browser thật
            redirect_headers = {
                "Referer": "https://id.zalo.me/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Upgrade-Insecure-Requests": "1",
            }
            
            redirect_resp = session.get(
                redirect_url, 
                headers=redirect_headers,
                proxies=proxies,
                allow_redirects=True,  # ✅ Cho phép follow redirect chain
                timeout=15
            )
            
            print(f"[REDIRECT] Final URL: {redirect_resp.url}")
            print(f"[REDIRECT] Status: {redirect_resp.status_code}")
            
        except Exception as e:
            print(f"[WARN] Redirect error (có thể bỏ qua): {e}")

        # --- SYNC COOKIES ---
        cookies = session.cookies.get_dict()
        
        print(f"\n[SYNC] Đồng bộ cookies sang .zalo.me domain...")
        for name, value in cookies.items():
            self.session.cookies.set(name, value, domain=".zalo.me")
        
        self.cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        
        print(f"[INFO] Total cookies: {len(cookies)}")
        print(f"[DEBUG] Cookie names: {list(cookies.keys())}")
        
        # ✅ Kiểm tra cookie quan trọng
        critical = ["zpsid", "zpw_sek"]
        missing = [c for c in critical if c not in cookies]
        if missing:
            print(f"⚠️ WARNING: Thiếu cookies: {missing}")
            print("💡 TIP: Có thể cần thử lại hoặc check network logs")
        else:
            print("✅ Đã có đủ cookies cần thiết!")
        
        return {"status": "ok"}


    # ==================== getLoginInfo() với debug tốt hơn ====================
    def getLoginInfo(self, imei=None, computer_name="Web", language="vi"):
        # 1. Xử lý IMEI (Bắt buộc dùng IMEI dài chuẩn Web)
        if not imei:
            if os.path.exists("imei.txt"):
                with open("imei.txt", "r") as f: imei = f.read().strip()
                if len(imei) < 50:
                    imei = self._generate_web_imei()
                    with open("imei.txt", "w") as f: f.write(imei)
            else:
                imei = self._generate_web_imei()
                with open("imei.txt", "w") as f: f.write(imei)

        print(f"\n[LOGIN INFO] IMEI: {imei[:30]}...")

        # 2. [MÔ PHỎNG JS] Tạo Payload Timestamp TRƯỚC (Thời điểm A)
        payload_ts = int(time.time() * 1000)

        # 3. [MÔ PHỎNG JS] Tạo Payload Object (CHƯA MÃ HÓA NGAY)
        # LƯU Ý: ĐÃ XÓA "is_new": True theo đúng logic JS (d=0)
        payload_dict = {
            "imei": imei,
            "computer_name": computer_name,
            "language": language,
            "ts": payload_ts
        }

        # 4. [MÔ PHỎNG JS] Gọi getServerInfo và Analytics (Tạo độ trễ mạng tự nhiên)
        self.submit_analytics()
        self.getServerInfo(imei)
        
        # Thêm chút delay nhỏ để giống mạng thật (JS await request)
        time.sleep(0.5) 

        # 5. [MÔ PHỎNG JS] Lấy Timestamp cho Cipher SAU (Thời điểm B)
        cipher_ts = int(time.time() * 1000)
        
        # Khởi tạo Cipher với timestamp B
        cipher_machine = ZaloParamCipher(self.zpw_type, imei, cipher_ts)
        
        my_zcid = cipher_machine.zcid
        my_zcid_ext = cipher_machine.zcid_ext

        # 6. Mã hóa Payload (Lúc này mới mã hóa payload đã tạo ở bước 3)
        # Payload giữ nguyên timestamp cũ (A), nhưng được mã hóa bởi Key sinh ra từ timestamp mới (B)
        encrypted_params = cipher_machine.encrypt_payload(payload_dict)

        # 7. Request
        url = "https://wpa.chat.zalo.me/api/login/getLoginInfo"
        
        query_params = {
            "zcid": my_zcid,
            "zcid_ext": my_zcid_ext,
            "enc_ver": "v2",
            "params": encrypted_params,
            "type": self.zpw_type,
            "client_version": self.zpw_ver,
            "nretry": 0
        }
        query_params["signkey"] = self._calculate_sign_key("getlogininfo", query_params)

        # Header tinh gọn, không ép Cookie
        req_headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": self.user_agent,
            "Referer": "https://chat.zalo.me/",
        }

        try:
            print(f"[REQUEST] ZCID: {my_zcid[:20]}...")
            resp = self.session.get(url, headers=req_headers, params=query_params, timeout=15)
            
            data = resp.json()
            
            if "data" in data and data["data"]:
                print("📩 Đang giải mã response...")
                result = cipher_machine.decrypt_response(data["data"])
                
                if result and "zpw_enk" in result:
                    self.secret_key_b64 = result["zpw_enk"]
                    print(f"💎 SECRET KEY THÀNH CÔNG: {self.secret_key_b64}")
                    with open("secret_key.txt", "w") as f: f.write(self.secret_key_b64)
                    return result
                else:
                    print(f"⚠️ Response decoded: {result}")
            else:
                print(f"⚠️ API Error: {data}")
            return data

        except Exception as e:
            print(f"❌ Error: {e}")
            return {"error": str(e)}
    def _calculate_sign_key(self, api_name: str, params: Dict) -> str:
        """
        [FIXED] Logic tính SignKey chuẩn từ Source Code Zalo JS.
        Logic: MD5("zsecure" + api_name + sorted_values)
        """
        # 1. Lấy danh sách key và sort a-z
        sorted_keys = sorted(params.keys())
        
        # 2. Khởi tạo chuỗi raw với SALT "zsecure"
        # Lưu ý: JS dùng "zsecure" + e (api_name)
        raw_string = f"zsecure{api_name}"
        
        # 3. Nối các value theo thứ tự key đã sort
        for key in sorted_keys:
            val = params[key]
            # Chuyển đổi sang string (nếu là int/float) để nối chuỗi
            raw_string += str(val)
            
        # 4. Debug in ra để kiểm tra nếu cần
        # print(f"[DEBUG] SignKey Raw String: {raw_string}")
        
        # 5. Trả về MD5 Hex
        return hashlib.md5(raw_string.encode('utf-8')).hexdigest()

    def _generate_web_imei(self):
        """
        [FIX 102] Tạo IMEI chuẩn Browser Zalo Web (Dài 69 ký tự)
        Format:   - 32_HEX_CHARS
        Kết quả ZCID sẽ dài 192 ký tự khớp với Golden Sample.
        """
        u = str(uuid.uuid4()) # 36 chars
        h = hashlib.md5(u.encode()).hexdigest() # 32 chars
        return f"{u}-{h}"

    def getServerInfo(self, imei):
        """Gọi API này để lấy cookie phiên (zpw_sec, viewerKey)"""
        url = "https://wpa.chat.zalo.me/api/login/getServerInfo"
        params = {
            "imei": imei,
            "type": self.zpw_type,
            "client_version": self.zpw_ver,
            "computer_name": "Web",
            "sp_mtn": 1,
            "bkt": 88
        }
        params["signkey"] = self._calculate_sign_key("getserverinfo", params)
        
        try:
            # Lưu ý: Cần update header để giống Chrome thật nhất
            resp = self.session.get(url, params=params, timeout=10)
            
            # data lúc này đã là dict, không phải string mã hóa
            data = resp.json() 
            
            # print(f"[OK] getServerInfo done. Status: {data}")
            # print(f"[DEBUG] Body: {data}") # In ra nếu muốn xem cấu trúc
            
        except Exception as e:
            print(f"[WARN] getServerInfo lỗi: {e}")
    def submit_analytics(self):
        """
        [NEW] Gọi API tracking za.zalo.me để lấy anoTok và làm sạch cookie __zi.
        Giúp server nhận diện đây là browser thật.
        """
        url = "https://za.zalo.me/v3/w/t"
        
        # Payload giả lập giống hệt browser
        payload = {
            "zl": self.chat_domain + "/",
            "zrf": "https://id.zalo.me/",
            "zch": "UTF-8",
            "zts": str(int(time.time() * 1000)),
            "zos": "Windows", # Hoặc MacOS tùy user_agent
            "zla": "vi,vi,en",
            "__zi": self.session.cookies.get("__zi", ""),
            "v": "2510081416", # Version tracking JS (có thể hardcode)
            "incog": "false",
            "zact": "pv",      # Page View
            "_zapp": "",
            "_zidnbaid": ""
        }
        
        headers = {
            "Origin": "https://chat.zalo.me",
            "Referer": "https://chat.zalo.me/",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }

        print("[ANALYTICS] Đang gửi tín hiệu tracking...")
        try:
            # Lưu ý: API này trả về JSON nhưng request dạng Form
            resp = self.session.post(url, data=payload, headers=headers, timeout=5)
            data = resp.json()
            
            if "anoTok" in data:
                print(f"[ANALYTICS] OK! Got anoTok: {data['anoTok'][:15]}...")
                # anoTok thường được Zalo dùng để check bot ẩn
            else:
                print(f"[ANALYTICS] Response: {data}")
                
        except Exception as e:
            print(f"[WARN] Analytics error: {e}")
# ==============================================================================
# PHẦN CHẠY THỬ (DÁN VÀO CUỐI FILE)
# ==============================================================================
if __name__ == "__main__":
    import sys

    # --- CẤU HÌNH ---
    TEST_PHONE = "0848888888" 
    MY_PROXY = None 
    proxies = {"http": MY_PROXY, "https": MY_PROXY} if MY_PROXY else None

    print("=== BẮT ĐẦU ZALO CFFI CLIENT ===")

    # Khởi tạo client (Lúc này session đã là curl_cffi)
    zalo = ZaloClient("", "")

    print("\n--- BƯỚC 1: ĐĂNG NHẬP ---")
    # wait_for_qr_login trả về status ok, cookie nằm trong zalo.cookie_string
    login_result = zalo.wait_for_qr_login(proxies=proxies)
    
    if not login_result:
        sys.exit()

    print("[SYNC] Nạp cookie vào Session...")
    zalo._load_cookies_to_session()

    # ✅ THÊM DELAY
    print("[WAIT] Đợi server activate session...")
    time.sleep(3)  # Đợi 3 giây

    print("\n--- BƯỚC 2: GỌI API LOGIN INFO (LẤY KEY) ---")

    print("\n--- BƯỚC 2: GỌI API LOGIN INFO (LẤY KEY) ---")
    try:
        zalo.getLoginInfo() 
    except Exception as e: 
        print(f"[ERROR] {e}")

    print("\n--- BƯỚC 3: TEST CHỨC NĂNG CHAT ---")
    if zalo.secret_key_b64:
        print(f"Đang tra cứu SĐT: {TEST_PHONE}...")
        user_info = zalo.getUserByPhone(TEST_PHONE, proxies=proxies)
        # ... (Phần in kết quả giữ nguyên) ...
    else:
        print("Chưa có Key.")
    
    print("\n=== KẾT THÚC ===")