import base64
import hashlib
import json
import time
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import uuid

class ZaloCrypto:
    ZCID_STATIC_KEY = bytes.fromhex("3FC4F0D2AB50057BCE0D90D9187A22B1")

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

    @staticmethod
    def generate_zcid(imei: str, type_val: str = "30") -> str:
        """
        Tạo ZCID từ IMEI và Timestamp.
        Công thức: AES_Encrypt(Key=StaticKey, Data="type,imei,timestamp")
        """
        try:
            timestamp = str(int(time.time() * 1000))
            # Cấu trúc dữ liệu gốc
            raw_data = f"{type_val},{imei},{timestamp}"
            
            # Mã hóa AES-CBC với Static Key, IV=0
            iv = b'\x00' * 16
            cipher = AES.new(ZaloCrypto.ZCID_STATIC_KEY, AES.MODE_CBC, iv=iv)
            
            # Pad dữ liệu và mã hóa
            padded_data = pad(raw_data.encode('utf-8'), 16)
            encrypted = cipher.encrypt(padded_data)
            
            # Trả về chuỗi Hex viết hoa
            return encrypted.hex().upper()
        except Exception as e:
            print(f"❌ Lỗi tạo ZCID: {e}")
            return ""

    @staticmethod
    def generate_zcid_ext() -> str:
        """Tạo zcid_ext ngẫu nhiên (thường là random string)"""
        return uuid.uuid4().hex[:10]

    @staticmethod
    def _derive_encrypt_key(zcid: str, zcid_ext: str) -> str:
        """Hàm nội bộ: Tạo key mã hóa động từ zcid và zcid_ext"""
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
        part3 = ''.join(zcid_processed["odd"][::-1][:12]) # Đảo ngược chuỗi lẻ
        
        return part1 + part2 + part3

    @staticmethod
    def encrypt_params(payload_dict: dict, zcid: str, zcid_ext: str) -> str:
        """Mã hóa payload params cho API getLoginInfo"""
        encrypt_key = ZaloCrypto._derive_encrypt_key(zcid, zcid_ext)
        print(f"🔑 Derived Encrypt Key: {encrypt_key}")
        
        try:
            key_bytes = encrypt_key.encode('utf-8')
            iv = b'\x00' * 16
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
            
            # Zalo yêu cầu JSON không có khoảng trắng thừa (separators)
            json_str = json.dumps(payload_dict, separators=(',', ':'))
            
            padded_data = pad(json_str.encode('utf-8'), 16)
            encrypted = cipher.encrypt(padded_data)
            
            # Encode Base64
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"❌ Mã hóa params thất bại: {e}")
            return ""

    @staticmethod
    def decrypt_response(encrypted_b64: str, zcid: str, zcid_ext: str):
        """Giải mã response từ API getLoginInfo"""
        encrypt_key = ZaloCrypto._derive_encrypt_key(zcid, zcid_ext)
        
        try:
            key_bytes = encrypt_key.encode('utf-8')
            iv = b'\x00' * 16
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv)
            
            encrypted_data = base64.b64decode(encrypted_b64)
            decrypted = cipher.decrypt(encrypted_data)
            
            unpadded = unpad(decrypted, 16)
            result = json.loads(unpadded.decode('utf-8'))
            return result
        except Exception as e:
            print(f"❌ Giải mã response thất bại: {e}")
            return None