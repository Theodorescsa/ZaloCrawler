# -*- coding: utf-8 -*-
import base64, json, hashlib
from urllib.parse import quote, unquote
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict


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
        zpw_ver: str = "670",
        zpw_type: str = "1000",
        user_agent: str = "Mozilla/5.0",
    ):
        self.secret_key_b64 = secret_key_b64
        self.cookie_string = cookie_string
        self.friend_domain = friend_domain.rstrip("/")
        self.zpw_ver = zpw_ver
        self.zpw_type = zpw_type
        self.user_agent = user_agent

        # cache key nếu muốn
        self._aes_key: Optional[bytes] = None

    # ---------- INTERNAL HELPERS ----------

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

    def _get(self, url: str, params: Optional[Dict] = None):
        return requests.get(url, headers=self._headers(), params=params, timeout=20)

    # ---------- PUBLIC API METHODS ----------

    def getUserByPhone(
        self,
        phone: str,
        reqSrc: Optional[str] = None,
        avatar_size: int = 240,
        language: str = "vi",
        imei: Optional[str] = None,
    ):
        import uuid

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
        print("Encrypted:",enc)
        print("imei:",imei)
        # input("Press Enter to continue...")
        url = f"{self.friend_domain}/api/friend/profile/get?{self._common_qs()}&params={quote(enc)}"
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
        import uuid
        
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