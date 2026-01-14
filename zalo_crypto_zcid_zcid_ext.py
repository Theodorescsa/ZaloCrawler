import base64
import json
import hashlib
import time
import uuid
import random
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

class ZaloCrypto:
    # [QUAN TRỌNG] Key này trong JS được parse UTF-8, nên nó là 32 bytes (AES-256)
    # Không được dùng bytes.fromhex()
    ZCID_STATIC_KEY = b"3FC4F0D2AB50057BCE0D90D9187A22B1"

    @staticmethod
    def _derive_encrypt_key_string(zcid: str, zcid_ext: str) -> str:
        """
        Tạo chuỗi Key (String) từ zcid và zcid_ext.
        Logic: MD5 Even + ZCID Even + ZCID Odd Reverse
        """
        # 1. MD5 của zcid_ext (Uppercase)
        md5_hash = hashlib.md5(zcid_ext.encode()).hexdigest().upper()
        
        # Helper tách chẵn lẻ (Index 0 là chẵn)
        def get_even_odd(s):
            return s[0::2], s[1::2]
        
        md5_even, _ = get_even_odd(md5_hash)
        zcid_even, zcid_odd = get_even_odd(zcid)
        
        # 2. Cắt và ghép chuỗi (Theo JS slice)
        part1 = md5_even[:8]
        part2 = zcid_even[:12]
        part3 = zcid_odd[::-1][:12] # Đảo ngược phần lẻ
        
        return part1 + part2 + part3

    @staticmethod
    def generate_zcid(imei: str, timestamp_ms: int, type_val: str = "30") -> str:
        """
        Tạo ZCID.
        [FIX] Nhận timestamp từ ngoài để đồng bộ với Payload.
        """
        try:
            # Format: type,imei,timestamp
            raw_data = f"{type_val},{imei},{timestamp_ms}"
            
            # AES-256 (Key 32 bytes UTF-8)
            iv = b'\x00' * 16
            cipher = AES.new(ZaloCrypto.ZCID_STATIC_KEY, AES.MODE_CBC, iv=iv)
            
            padded_data = pad(raw_data.encode('utf-8'), 16)
            encrypted = cipher.encrypt(padded_data)
            
            return encrypted.hex().upper()
        except Exception as e:
            print(f"❌ Lỗi tạo ZCID: {e}")
            return ""

    @staticmethod
    def generate_zcid_ext() -> str:
        """
        Tạo zcid_ext.
        JS: randomString(6, 12).
        Lấy ngẫu nhiên độ dài từ 6-12 ký tự hex.
        """
        length = random.randint(6, 12)
        # uuid4().hex đủ dài, cắt lấy length ký tự
        return uuid.uuid4().hex[:length]

    @staticmethod
    def encrypt_params(payload_dict: dict, zcid: str, zcid_ext: str) -> str:
        """Mã hóa payload params"""
        encrypt_key_str = ZaloCrypto._derive_encrypt_key_string(zcid, zcid_ext)
        print(f"🔑 Derived Key String: {encrypt_key_str}")
        
        try:
            # [FIX QUAN TRỌNG] JS dùng Utf8.parse(key_str) -> AES-256
            key_bytes = encrypt_key_str.encode('utf-8')
            
            iv = b'\x00' * 16
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
            
            # JSON Compact (không khoảng trắng)
            json_str = json.dumps(payload_dict, separators=(',', ':'))
            
            padded_data = pad(json_str.encode('utf-8'), 16)
            encrypted = cipher.encrypt(padded_data)
            
            # Output: Base64
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"❌ Mã hóa thất bại: {e}")
            return ""

    @staticmethod
    def decrypt_response(encrypted_b64: str, zcid: str, zcid_ext: str):
        """Giải mã response từ server"""
        encrypt_key_str = ZaloCrypto._derive_encrypt_key_string(zcid, zcid_ext)
        
        try:
            # [FIX QUAN TRỌNG] AES-256
            key_bytes = encrypt_key_str.encode('utf-8')
            
            iv = b'\x00' * 16
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
            
            encrypted_data = base64.b64decode(encrypted_b64)
            decrypted = cipher.decrypt(encrypted_data)
            unpadded = unpad(decrypted, 16)
            
            return json.loads(unpadded.decode('utf-8'))
        except Exception as e:
            print(f"❌ Giải mã thất bại: {e}")
            return None