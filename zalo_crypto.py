import base64
import hashlib
import json
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

class ZaloLogin:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://chat.zalo.me/',
            'Origin': 'https://chat.zalo.me'
        })
        self.zcid = None
        self.zcid_ext = None
        self.cookies = None

    def login_with_credentials(self, phone_number, password):
        """
        Đăng nhập Zalo bằng số điện thoại và mật khẩu
        Lưu ý: Đây là ví dụ minh họa, Zalo có thể thay đổi API
        """
        print(f"🔐 Đang đăng nhập với số điện thoại: {phone_number}")
        
        # Bước 1: Lấy thông tin đăng nhập ban đầu
        init_url = "https://login.zaloapp.com/v3/api/auth/login"
        init_data = {
            "phone": phone_number,
            "password": password,
            "client_version": "670",
            "type": "30"
        }
        
        try:
            response = self.session.post(init_url, json=init_data)
            if response.status_code == 200:
                result = response.json()
                if result.get("error_code") == 0:
                    print("✅ Đăng nhập thành công")
                    self._extract_login_info()
                    return True
                else:
                    print(f"❌ Lỗi đăng nhập: {result.get('error_message')}")
                    return False
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Lỗi khi đăng nhập: {e}")
            return False

    def login_with_cookies(self, cookies_dict):
        """
        Đăng nhập bằng cookies có sẵn
        """
        print("🍪 Đang đăng nhập bằng cookies...")
        self.session.cookies.update(cookies_dict)
        self.cookies = cookies_dict
        return self._extract_login_info()

    def _extract_login_info(self):
        """
        Trích xuất thông tin đăng nhập từ cookies và session
        """
        try:
            # Lấy zcid và zcid_ext từ cookies
            cookies_dict = self.session.cookies.get_dict()
            self.cookies = cookies_dict
            
            # Tìm zcid và zcid_ext trong cookies
            zcid = cookies_dict.get('zcid')
            zcid_ext = cookies_dict.get('zcid_ext')
            
            if not zcid or not zcid_ext:
                print("⚠️ Không tìm thấy zcid hoặc zcid_ext trong cookies, thử phương pháp khác...")
                return self._get_login_info_from_api()
            
            self.zcid = zcid
            self.zcid_ext = zcid_ext
            print(f"📋 ZCID: {zcid}")
            print(f"📋 ZCID_EXT: {zcid_ext}")
            
            return True
            
        except Exception as e:
            print(f"❌ Lỗi khi trích xuất thông tin đăng nhập: {e}")
            return False

    def _get_login_info_from_api(self):
        """
        Gọi API getLoginInfo để lấy thông tin đăng nhập
        """
        print("🔍 Đang gọi API getLoginInfo...")
        
        # Tạo URL với các tham số mẫu (cần điều chỉnh theo thực tế)
        base_url = "https://wpa.chat.zalo.me/api/login/getLoginInfo"
        
        # Thử với các tham số mặc định
        params = {
            "client_version": "670",
            "type": "30",
            "nretry": "0"
        }
        
        try:
            response = self.session.get(base_url, params=params)
            if response.status_code == 200:
                result = response.json()
                print(f"📊 Response từ getLoginInfo: {result}")
                
                # Phân tích URL để lấy zcid và zcid_ext
                request_url = response.request.url
                self._parse_zcid_from_url(request_url)
                
                return True
            else:
                print(f"❌ Lỗi khi gọi getLoginInfo: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi khi gọi API getLoginInfo: {e}")
            return False

    def _parse_zcid_from_url(self, url):
        """
        Phân tích URL để trích xuất zcid và zcid_ext
        """
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            zcid = query_params.get('zcid', [None])[0]
            zcid_ext = query_params.get('zcid_ext', [None])[0]
            
            if zcid and zcid_ext:
                self.zcid = zcid
                self.zcid_ext = zcid_ext
                print(f"📋 ZCID (từ URL): {zcid}")
                print(f"📋 ZCID_EXT (từ URL): {zcid_ext}")
                return True
            else:
                print("⚠️ Không tìm thấy zcid và zcid_ext trong URL")
                return False
                
        except Exception as e:
            print(f"❌ Lỗi khi phân tích URL: {e}")
            return False

    def get_encrypted_data(self):
        """
        Lấy dữ liệu encrypted từ API getLoginInfo
        """
        if not self.zcid or not self.zcid_ext:
            print("❌ Chưa có thông tin zcid và zcid_ext")
            return None
        
        print("🔐 Đang lấy dữ liệu encrypted từ API...")
        
        url = "https://wpa.chat.zalo.me/api/login/getLoginInfo"
        params = {
            "zcid": self.zcid,
            "zcid_ext": self.zcid_ext,
            "enc_ver": "v2",
            "type": "30",
            "client_version": "670",
            "nretry": "0"
        }
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 200:
                result = response.json()
                print(f"📊 Kết quả API: {result}")
                
                if result.get("error_code") == 0:
                    encrypted_data = result.get("data", "")
                    print(f"🔐 Dữ liệu encrypted: {encrypted_data}")
                    return encrypted_data
                else:
                    print(f"❌ Lỗi từ API: {result.get('error_message')}")
                    return None
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Lỗi khi lấy dữ liệu encrypted: {e}")
            return None

    def get_login_info(self):
        """
        Lấy thông tin đăng nhập đầy đủ và giải mã
        """
        # Lấy thông tin đăng nhập cơ bản
        if not self._extract_login_info():
            return None
        
        # Lấy dữ liệu encrypted
        encrypted_b64 = self.get_encrypted_data()
        if not encrypted_b64:
            return None
        
        # Giải mã dữ liệu
        decrypted_data = ZaloCrypto.decrypt_with_zcid(encrypted_b64, self.zcid, self.zcid_ext)
        
        result = {
            "zcid": self.zcid,
            "zcid_ext": self.zcid_ext,
            "encrypted_data": encrypted_b64,
            "decrypted_data": decrypted_data,
            "cookies": self.cookies
        }
        
        return result

# Sử dụng
if __name__ == "__main__":
    # Tạo instance ZaloLogin
    zalo_login = ZaloLogin()
    
    # Phương án 1: Đăng nhập bằng cookies có sẵn
    existing_cookies = {
        # Thêm cookies của bạn ở đây
        # 'zcid': 'your_zcid_here',
        # 'zcid_ext': 'your_zcid_ext_here',
        # ... các cookies khác
    }
    
    if existing_cookies:
        login_success = zalo_login.login_with_cookies(existing_cookies)
    else:
        # Phương án 2: Đăng nhập bằng tài khoản (cần điều chỉnh theo API thực tế)
        phone_number = "your_phone_number"
        password = "your_password"
        login_success = zalo_login.login_with_credentials(phone_number, password)
    
    if login_success:
        # Lấy thông tin đăng nhập đầy đủ
        login_info = zalo_login.get_login_info()
        
        if login_info:
            print("\n" + "="*50)
            print("✅ THÔNG TIN ĐĂNG NHẬP HOÀN CHỈNH")
            print("="*50)
            print(f"ZCID: {login_info['zcid']}")
            print(f"ZCID_EXT: {login_info['zcid_ext']}")
            print(f"Encrypted Data: {login_info['encrypted_data'][:100]}...")
            print(f"Decrypted Data: {json.dumps(login_info['decrypted_data'], indent=2, ensure_ascii=False)}")
            print(f"Cookies: {login_info['cookies']}")
            
            # Lưu kết quả giải mã vào file
            with open("zalo_login_info.json", "w", encoding="utf-8") as f:
                json.dump(login_info, f, indent=2, ensure_ascii=False, default=str)
            print("💾 Đã lưu thông tin vào file: zalo_login_info.json")
        else:
            print("❌ Không thể lấy thông tin đăng nhập")
    else:
        print("❌ Đăng nhập thất bại")
        

