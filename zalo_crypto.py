import base64
import hashlib
import json
import time
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

class ZaloCrypto:
    @staticmethod
    def decrypt_with_zcid(encrypted_b64, zcid, zcid_ext):
        """Giải mã dữ liệu Zalo khi biết zcid và zcid_ext"""
        # Tạo encrypt_key từ zcid và zcid_ext
        md5_hash = hashlib.md5(zcid_ext.encode()).hexdigest().upper()
        
        def process_str(s):
            even_chars = []
            odd_chars = []
            for i, char in enumerate(s):
                if i % 2 == 0:
                    even_chars.append(char)
                else:
                    odd_chars.append(char)
            return {"even": even_chars, "odd": odd_chars}
        
        md5_processed = process_str(md5_hash)
        zcid_processed = process_str(zcid)
        
        part1 = ''.join(md5_processed["even"][:8])
        part2 = ''.join(zcid_processed["even"][:12])
        part3 = ''.join(zcid_processed["odd"][::-1][:12])
        encrypt_key = part1 + part2 + part3
        
        print("ENCRYPT_KEY:", encrypt_key)
        
        try:
            key_bytes = encrypt_key.encode('utf-8')
            iv = b'\x00' * 16
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
            encrypted_data = base64.b64decode(encrypted_b64)
            decrypted = cipher.decrypt(encrypted_data)
            unpadded = unpad(decrypted, 16)
            result = json.loads(unpadded.decode('utf-8'))
            print("✅ GIẢI MÃ THÀNH CÔNG!")
            return result
        except Exception as e:
            print(f"❌ Giải mã thất bại: {e}")
            return None

    @staticmethod
    def encrypt_with_zcid(data_dict, zcid, zcid_ext):
        """Mã hóa dữ liệu Zalo khi biết zcid và zcid_ext"""
        # Tạo encrypt_key từ zcid và zcid_ext (tương tự decrypt)
        md5_hash = hashlib.md5(zcid_ext.encode()).hexdigest().upper()
        
        def process_str(s):
            even_chars = []
            odd_chars = []
            for i, char in enumerate(s):
                if i % 2 == 0:
                    even_chars.append(char)
                else:
                    odd_chars.append(char)
            return {"even": even_chars, "odd": odd_chars}
        
        md5_processed = process_str(md5_hash)
        zcid_processed = process_str(zcid)
        
        part1 = ''.join(md5_processed["even"][:8])
        part2 = ''.join(zcid_processed["even"][:12])
        part3 = ''.join(zcid_processed["odd"][::-1][:12])
        encrypt_key = part1 + part2 + part3
        
        try:
            key_bytes = encrypt_key.encode('utf-8')
            iv = b'\x00' * 16
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
            json_str = json.dumps(data_dict, separators=(',', ':'))
            padded_data = pad(json_str.encode('utf-8'), 16)
            encrypted = cipher.encrypt(padded_data)
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"❌ Mã hóa thất bại: {e}")
            return None
