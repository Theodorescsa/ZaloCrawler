# -*- coding: utf-8 -*-
import base64, json, hashlib
from urllib.parse import quote, unquote
import requests
from Crypto.Cipher import AES
from typing import Optional, Dict

# ====== CONFIG BẮT BUỘC (điền của bạn) ======
# Lấy ở DevTools → Application → Cookies (https://chat.zalo.me)
SECRET_KEY_B64 = '8Kow7PvOwmzy4f/c3TR6rg=='# a.default.getSecretKey() (chuỗi base64)
COOKIE_STRING = (
    "ozi=2000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbwrAxraqyOtpIUfVUMIX7VCj6bz9865zatrQNyD3ar.1; _ga_1J0YGQPT22=GS1.1.1743267239.1.1.1743267278.21.0.0; _gid=GA1.2.1327484270.1762224522; _zlang=vn; _gcl_au=1.1.1210773121.1762247361; _fbp=fb.1.1762247361146.837283859710473447; zoaw_sek=G7JG.1719398236.2.CzqLYgAU_zJ-SOIoefx_rAAU_zIYdl_KermztSkU_zG; zoaw_type=0; _ga_NVN38N77J3=GS2.2.s1762247366$o2$g1$t1762247725$j52$l0$h0; _ga_E63JS7SPBL=GS2.1.s1762247360$o3$g1$t1762249231$j60$l0$h0; _ga_WSPJQT0ZH1=GS2.1.s1762247465$o1$g1$t1762249231$j60$l0$h0; __zi=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayVtJ6VhF2SJXoGEPwjl9f86PGvbgYnDG.1; __zi-legacy=3000.SSZzejyD2DyiZwEqqGn1pJ75lh39JHN1E8Yy_zm36zbxrAxraayVtJ6VhF2SJXoGEPwjl9f86PGvbgYnDG.1; app.event.zalo.me=1284945502602914140; _ga_907M127EPP=GS2.1.s1762402675$o2$g1$t1762402851$j60$l0$h0; _ga_RYD7END4JE=GS2.2.s1762412863$o16$g1$t1762412865$j58$l0$h0; _ga_YS1V643LGV=GS2.1.s1762412863$o14$g0$t1762412865$j58$l0$h0; _ga=GA1.2.759643980.1743071453; _gat=1; _ga_3EM8ZPYYN3=GS2.2.s1762417460$o14$g1$t1762419721$j60$l0$h0; zpsid=nzx5.447761965.43.t_JTcV7Nh9tScHo7_TUidOIatgd5u9khmEwQg8MzpVhloWiwyCJ8aPZNh9q; zpw_sek=Ad-w.447761965.a0.pLzD0vsCmDgmmd30l8p0skQkfR6_jkBYrkEtxStwZwtmzhdk-wEZwSdUzgZwiVtuuFYgk_gItNqwZTE-aUN0sW"
)
FRIEND_DOMAIN = "https://tt-friend-wpa.chat.zalo.me"
ZPW_VER = "670"
ZPW_TYPE = "30"
# ============================================= #


def _b64decode_padded(s: str) -> bytes:
    s = s.strip().replace(" ", "+")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)

def _b64encode_nopad(b: bytes) -> str:
    return base64.b64encode(b).decode().rstrip("=")

def _pkcs7_pad(b: bytes, block: int = 16) -> bytes:
    pad = block - (len(b) % block)
    return b + bytes([pad])*pad

def _pkcs7_unpad(b: bytes) -> bytes:
    if not b:
        return b
    p = b[-1]
    if p < 1 or p > 16 or b[-p:] != bytes([p])*p:
        raise ValueError("Bad PKCS7 padding")
    return b[:-p]

def _get_aes_key() -> bytes:
    key = _b64decode_padded(SECRET_KEY_B64)
    # CryptoJS dùng raw key 16/24/32 bytes. Nếu độ dài ko đúng, sha256 cho 32b (phòng khi bundle đổi format).
    if len(key) not in (16, 24, 32):
        key = hashlib.sha256(key).digest()
    return key

def encodeAES(plaintext: str) -> str:
    """CryptoJS AES-CBC(IV=0...0, PKCS7), output base64"""
    key = _get_aes_key()
    iv = bytes(16)  # 16 zero bytes
    pt = plaintext.encode("utf-8")
    ct = AES.new(key, AES.MODE_CBC, iv=iv).encrypt(_pkcs7_pad(pt))
    return _b64encode_nopad(ct)  # web thường không cần '=' padding

def decodeAES(cipher_b64_or_url: str) -> str:
    """Giải mã ciphertext base64 (URL-encoded ok)"""
    # chấp nhận input là URL-encoded
    try:
        cipher_b64_or_url = unquote(cipher_b64_or_url)
    except Exception:
        pass
    key = _get_aes_key()
    iv = bytes(16)
    # chấp nhận thiếu padding
    cipher = cipher_b64_or_url.strip().replace(" ", "+")
    cipher += "=" * (-len(cipher) % 4)
    ct = base64.b64decode(cipher)
    pt = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct)
    return _pkcs7_unpad(pt).decode("utf-8", "ignore")

def _headers():
    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://chat.zalo.me",
        "Referer": "https://chat.zalo.me/",
        "Cookie": COOKIE_STRING,  # <<— add this line
    }

def _common_qs():
    return f"zpw_ver={ZPW_VER}&zpw_type={ZPW_TYPE}"

def _get(url: str, params: Optional[Dict] = None):
    return requests.get(url, headers=_headers(), params=params, timeout=20)

# ---------- API CALLS ----------
def getUserByPhone(phone, reqSrc=None, avatar_size=240, language="vi", imei=None):
    import uuid, json
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
    enc = encodeAES(data_str)

    # URL-encode the params (safer)
    url = f"{FRIEND_DOMAIN}/api/friend/profile/get?{_common_qs()}&params={quote(enc)}"
    resp = _get(url)
    resp.raise_for_status()
    j = resp.json()

    if j.get("error_code") != 0:
        raise RuntimeError(f"API error: {j}")

    plaintext = decodeAES(j["data"])
    try:
        return json.loads(plaintext)
    except Exception:
        return {"raw": plaintext}

def getMultiUsersByPhones(phones, avatar_size=240, language="vi"):
    """
    Lấy thông tin nhiều người dùng bằng số điện thoại
    
    Args:
        phones: Danh sách số điện thoại (list of strings)
        avatar_size: Kích thước avatar (mặc định 240)
        language: Ngôn ngữ (mặc định "vi")
    
    Returns:
        Dictionary chứa thông tin người dùng
    """
    import uuid, json
    
    payload = {
        "phones": phones,
        "avatar_size": avatar_size,
        "language": language
    }

    data_str = json.dumps(payload, ensure_ascii=False)
    enc = encodeAES(data_str)

    url = f"{FRIEND_DOMAIN}/api/friend/profile/multiget?{_common_qs()}&params={quote(enc)}"
    resp = _get(url)
    resp.raise_for_status()
    j = resp.json()

    if j.get("error_code") != 0:
        raise RuntimeError(f"API error: {j}")

    plaintext = decodeAES(j["data"])
    try:
        return json.loads(plaintext)
    except Exception:
        return {"raw": plaintext}