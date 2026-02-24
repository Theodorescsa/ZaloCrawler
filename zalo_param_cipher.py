import hashlib
import base64
import time
import json
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

class ZaloParamCipher:
    def __init__(self, zpw_type, imei, timestamp):
        self.zpw_type = str(zpw_type)
        self.imei = str(imei)
        self.timestamp = str(timestamp)
        self.zcid = None
        self.zcid_ext = None
        self.encrypt_key = None
        
        # [QUAN TRỌNG] Key gốc là chuỗi string 32 ký tự
        # JS dùng Utf8.parse() nên ta phải encode() sang bytes chứ không dùng fromhex()
        # 32 bytes = AES-256
        self.ZCID_STATIC_KEY = "3FC4F0D2AB50057BCE0D90D9187A22B1".encode('utf-8')

        # 1. Tạo ZCID
        self._generate_zcid()
        
        # 2. Tạo Key
        self._generate_keys()

    def _process_str(self, s):
        if not s or not isinstance(s, str):
            return None, None
        even = []
        odd = []
        for i, char in enumerate(s):
            if i % 2 == 0:
                even.append(char)
            else:
                odd.append(char)
        return even, odd

    def _generate_zcid(self):
        # Format: type,imei,ts
        raw_data = f"{self.zpw_type},{self.imei},{self.timestamp}"
        
        iv = bytes(16)
        # Sử dụng Key 32 bytes -> AES-256
        cipher = AES.new(self.ZCID_STATIC_KEY, AES.MODE_CBC, iv)
        
        padded_data = pad(raw_data.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        
        # JS toUpperCase()
        self.zcid = encrypted.hex().upper()

    def _try_create_encrypt_key(self, zcid_ext, zcid):
        md5_ext = hashlib.md5(zcid_ext.encode()).hexdigest().upper()
        
        even_n, _ = self._process_str(md5_ext)
        even_a, odd_s = self._process_str(zcid)
        
        if not even_n or not even_a or not odd_s:
            return None
        
        part1 = "".join(even_n[:8])
        part2 = "".join(even_a[:12])
        part3 = "".join(odd_s[::-1][:12])
        
        return part1 + part2 + part3

    def _generate_keys(self):
        attempt = 0
        while attempt < 50:
            # Random độ dài 6-12 (như request mẫu của bạn là 9 ký tự)
            rand_len = random.randint(6, 12)
            hex_chars = "0123456789abcdef"
            self.zcid_ext = "".join(random.choice(hex_chars) for _ in range(rand_len))
            
            key = self._try_create_encrypt_key(self.zcid_ext, self.zcid)
            
            if key and len(key) == 32:
                self.encrypt_key = key
                return
            attempt += 1
        raise Exception("Failed to generate valid Encrypt Key")

    def encrypt_payload(self, payload_dict):
        if not self.encrypt_key: raise Exception("No Key")
        
        # separators=(',', ':') để loại bỏ khoảng trắng thừa giống JS
        json_str = json.dumps(payload_dict, separators=(',', ':'), ensure_ascii=False)
        
        # Key derived cũng là 32 ký tự string -> encode utf-8 -> 32 bytes key
        key_bytes = self.encrypt_key.encode('utf-8')
        iv = bytes(16)
        
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
        padded = pad(json_str.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded)
        
        # Base64 no padding
        return base64.b64encode(encrypted).decode().strip()

    def decrypt_response(self, encrypted_b64):
        if not encrypted_b64: return None
        try:
            encrypted_b64 = encrypted_b64.strip().replace(" ", "+")
            encrypted_b64 += "=" * (-len(encrypted_b64) % 4)
            
            ct = base64.b64decode(encrypted_b64)
            key_bytes = self.encrypt_key.encode('utf-8')
            iv = bytes(16)
            
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ct)
            pt = unpad(decrypted, AES.block_size)
            return json.loads(pt.decode('utf-8'))
        except Exception as e:
            print(f"[Decrypt Error] {e}")
            return None