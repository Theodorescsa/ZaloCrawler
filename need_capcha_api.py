#!/usr/bin/env python3
"""
Zalo Login Simulator - Get Captcha Image and Token
"""

import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from urllib.parse import urlencode
import binascii
import json

# ==================== CẤU HÌNH ====================

# Public key từ Zalo
RSA_MODULUS_HEX = (
    'be6b22d708d62b9733a42b8d92dac5ebc5eac0515bf1c825c67211e3c3c11d56'
    '908054f288c46ca7706ec856907765a6aee596acc5c44958a5f0dfdd0b47f476'
    '8f9f7dbac015e83b5c7e6404562b2b8ac082a3ffa538dd54c71466f990686985'
    'e40c5b0ae57bb44d72056deba79f71aeb8350353920e5add0cfc4b3e2064a552'
    'c2f6a357cbdb18dd169f297f91683e0355d1b4d0280cc6eee144a6bd01e52835'
    '3b4002ccdfc3010545d1648c561af9abb0d02aaf28d83172083de92d8dbca7c8'
    '52535c0b60a0ae8de9eab811df7d7a7f35003c7ff9542c83a3a9f2975cfbbb19'
    '8c7d9241e03e60557e51a589b9e82a342fdf8c34d98404a4f6c1526bd1bb3655'
)

RSA_EXPONENT = 65537

# API endpoints
API_NEED_CAPTCHA = "https://id.zalo.me/account/authen/need-captcha"
API_LOGIN_PWD = "https://id.zalo.me/account/authen/pwd"
LOGIN_PAGE = "https://id.zalo.me/account/login"
API_GET_CAPTCHA = "https://zcaptcha.api.zaloapp.com/api/get-captcha"

# Các tham số được mã hóa
SECURE_PARAMS = ["phone", "password"]

VERSION = "5.6.0"

# ==================== LỚP ZALO LOGIN ====================

class ZaloLogin:
    def __init__(self):
        self.session = requests.Session()
        self.rsa_key = self._build_rsa_key()
        self.captcha_token = None
        self.captcha_image_url = None
        
        # Headers cố định
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://id.zalo.me",
            "Referer": "https://id.zalo.me/account/login",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        })
        
        # Lấy session mới
        self._get_fresh_session()
    
    def _build_rsa_key(self):
        """Tạo RSA public key từ modulus và exponent."""
        n = int(RSA_MODULUS_HEX, 16)
        e = RSA_EXPONENT
        return RSA.construct((n, e))
    
    def _get_fresh_session(self):
        """Lấy session mới từ trang login."""
        print("🔄 Đang lấy session mới...")
        try:
            headers = {
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            }
            
            response = self.session.get(LOGIN_PAGE, headers=headers, timeout=10)
            print(f"✅ Session mới đã được tạo")
            print(f"   Cookies: {list(self.session.cookies.keys())}")
            return True
        except Exception as e:
            print(f"❌ Lỗi khi lấy session: {e}")
            return False
    
    def rsa_encrypt(self, plaintext: str) -> str:
        """Mã hóa RSA PKCS#1 v1.5, trả về hex string."""
        cipher = PKCS1_v1_5.new(self.rsa_key)
        ciphertext_bytes = cipher.encrypt(plaintext.encode('utf-8'))
        return binascii.hexlify(ciphertext_bytes).decode('ascii')
    
    def process_payload(self, params: dict) -> dict:
        """Mã hóa các tham số nhạy cảm."""
        processed = params.copy()
        
        for key in SECURE_PARAMS:
            if key in processed and processed[key]:
                plaintext = str(processed[key])
                encrypted_hex = self.rsa_encrypt(plaintext)
                processed[key] = encrypted_hex
                print(f"[Encrypted] {key}: {plaintext} -> {encrypted_hex[:40]}...")
        
        return processed
    
    def _format_phone(self, phone: str) -> str:
        """Định dạng số điện thoại đúng chuẩn."""
        phone = ''.join(filter(str.isdigit, phone))
        
        if phone.startswith('0'):
            phone = '84' + phone[1:]
        elif not phone.startswith('84'):
            phone = '84' + phone
        
        return phone
    
    def get_captcha_from_browser_method(self):
        """
        Phương pháp lấy captcha bằng cách mô phỏng trình duyệt.
        Sử dụng các tham số từ request thực tế.
        """
        print("🔄 Đang lấy captcha bằng phương pháp mô phỏng trình duyệt...")
        
        # Headers từ request thực tế
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "vi,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
            "Content-Length": "2",
            "Origin": "https://zcaptcha.api.zaloapp.com",
            "Referer": "https://zcaptcha.api.zaloapp.com/zcaptcha-challenge?appId=3032357805345395173&lang=vi",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=1, i",
            "Pragma": "no-cache",
            "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not=A?Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        
        # Thêm cookies quan trọng
        cookies = {
            "__zi": "3000.QOBlzDCV2uGerkFzm0LLr63HuVh70XZNPDEl-C8D7jndsgZt.1",
            "csrf-token": "G1WuIeYEcoyAO6HQX8wFFr0m9X_ArSCEEoWeQ-o5XaizD6CsfuB0NsKyQtVpZiaIPtDj9xhDtWLcHd0lkxkDMJHIU2s-j8POD5nsA7q"
        }
        
        # try:
            # Tạo session riêng cho captcha
        captcha_session = requests.Session()
        captcha_session.headers.update(headers)
        captcha_session.cookies.update(cookies)
        
        # Gửi request empty payload
        response = captcha_session.post(
            API_GET_CAPTCHA,
            data="{}",
            timeout=15
        )
        
        print(f"[Captcha API] Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('error_code') == 0:
                data = result.get('data', {})
                image_data = data.get('image', {})
                
                captcha_info = {
                    'success': True,
                    'image_url': image_data.get('url'),
                    'token': image_data.get('token'),
                    'question': data.get('question'),
                    'expired_secs': data.get('expiredSecs'),
                    'session': captcha_session,
                    'full_response': result
                }
                
                print(f"✅ Đã lấy captcha thành công!")
                print(f"   Câu hỏi: {captcha_info['question']}")
                print(f"   Token: {captcha_info['token']}")
                print(f"   Image URL: {captcha_info['image_url']}")
                print(f"   Expires in: {captcha_info['expired_secs']}s")
                
                # Lưu thông tin captcha
                self.captcha_token = captcha_info['token']
                self.captcha_image_url = captcha_info['image_url']
                
                return captcha_info
            else:
                error_msg = result.get('error_message', 'Unknown error')
                error_code = result.get('error_code')
                print(f"Kết quả API: {result}")
                print(f"❌ Lỗi captcha API: {error_code} - {error_msg}")
                return {
                    'success': False,
                    'error': error_msg,
                    'error_code': error_code
                }
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return {
                'success': False,
                'error': f"HTTP {response.status_code}"
            }
            
        # except Exception as e:
        #     print(f"❌ Lỗi khi lấy captcha: {e}")
        #     return {
        #         'success': False,
        #         'error': str(e)
        #     }
    
    def download_captcha_image(self, image_url: str, session=None, save_path: str = "captcha_image.jpg"):
        """Tải ảnh captcha về."""
        try:
            print(f"📥 Đang tải ảnh captcha...")
            
            if session is None:
                session = self.session
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://zcaptcha.api.zaloapp.com/",
            }
            
            response = session.get(image_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"✅ Đã lưu ảnh captcha: {save_path}")
                return {'success': True, 'image_path': save_path}
            else:
                print(f"❌ Lỗi tải ảnh: {response.status_code}")
                return {'success': False, 'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Lỗi khi tải ảnh captcha: {e}")
            return {'success': False, 'error': str(e)}
    
    def solve_captcha_interactive(self, captcha_info: dict):
        """Giải captcha tương tác - hiển thị ảnh và nhập kết quả."""
        if not captcha_info['success']:
            print("❌ Không thể lấy thông tin captcha")
            return None
        
        print("\n" + "="*50)
        print("🛡️ GIẢI CAPTCHA")
        print("="*50)
        print(f"❓ Câu hỏi: {captcha_info['question']}")
        print(f"⏰ Thời hạn: {captcha_info['expired_secs']} giây")
        print(f"🔑 Token: {captcha_info['token']}")
        
        # Tải ảnh captcha
        session = captcha_info.get('session', self.session)
        image_result = self.download_captcha_image(
            captcha_info['image_url'], 
            session=session
        )
        
        if image_result['success']:
            print(f"📷 Ảnh captcha đã được lưu: {image_result['image_path']}")
            print("   Mở file này để xem ảnh captcha")
        else:
            print(f"📷 Link ảnh captcha: {captcha_info['image_url']}")
        
        print("\n💡 Hướng dẫn:")
        print("   - Mở ảnh captcha_image.jpg")
        print("   - Xác định các hình ảnh đúng với câu hỏi")
        print("   - Nhập số thứ tự các hình (từ 0-8), cách nhau bằng dấu phẩy")
        print("   - VD: 1,3,5 hoặc 0,2,4,6")
        
        while True:
            try:
                user_input = input("\nNhập số thứ tự các hình (0-8): ").strip()
                
                if not user_input:
                    print("⚠️ Vui lòng nhập ít nhất một số!")
                    continue
                
                indices = [int(x.strip()) for x in user_input.split(',')]
                
                if all(0 <= idx <= 8 for idx in indices):
                    captcha_response = f"{captcha_info['token']}|{','.join(map(str, indices))}"
                    print(f"✅ Đã nhập: {indices}")
                    print(f"📤 Captcha response: {captcha_response}")
                    return captcha_response
                else:
                    print("⚠️ Số phải trong khoảng 0-8!")
                    
            except ValueError:
                print("⚠️ Định dạng không hợp lệ! Ví dụ: 1,3,5")
            except KeyboardInterrupt:
                print("\n⏹️ Đã hủy giải captcha")
                return None
    
    def check_need_captcha(self, phone: str):
        """Kiểm tra xem có cần captcha không."""
        formatted_phone = self._format_phone(phone)
        
        params = {
            "phone": formatted_phone,
            "v": VERSION,
            "continue": "https://chat.zalo.me/",
        }
        
        payload = self.process_payload(params)
        body = urlencode(payload)
        
        print(f"[Captcha Check] Số điện thoại: {formatted_phone}")
        
        try:
            response = self.session.post(
                API_NEED_CAPTCHA,
                data=body,
                timeout=15
            )
            
            print(f"[Captcha Check] Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    print(f"[Captcha Check] Response không phải JSON: {response.text[:200]}")
                    return {
                        'success': False,
                        'error': 'Invalid JSON response'
                    }
                
                data = result.get('data', {}) if result else {}
                need_captcha = data.get('needCaptcha', False) if data else False
                captcha_type = data.get('captchaType', '') if data else ''
                
                print(f"[Captcha Check] Kết quả: {'CẦN captcha' if need_captcha else 'KHÔNG cần captcha'}")
                if captcha_type:
                    print(f"[Captcha Check] Loại captcha: {captcha_type}")
                
                return {
                    'success': True,
                    'need_captcha': need_captcha,
                    'captcha_type': captcha_type,
                    'full_response': result
                }
            else:
                print(f"[Captcha Check] Lỗi HTTP: {response.status_code}")
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'response_text': response.text[:500]
                }
                
        except Exception as e:
            print(f"[Captcha Check] Lỗi: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def login_with_password(self, phone: str, password: str, captcha_response: str = None):
        """Đăng nhập với password (có hoặc không có captcha)."""
        formatted_phone = self._format_phone(phone)
        
        params = {
            "phone": formatted_phone,
            "password": password,
            "iso_country_code": "VN",
            "v": VERSION,
            "continue": "https://chat.zalo.me/",
        }
        
        # Thêm captcha nếu có
        if captcha_response:
            params["captcha-response"] = captcha_response
            params["captcha-version"] = "zcaptcha"
            print(f"[Login] Sử dụng captcha response: {captcha_response}")
        
        payload = self.process_payload(params)
        body = urlencode(payload)
        
        print(f"[Login] Đang đăng nhập với số điện thoại: {formatted_phone}")
        
        try:
            response = self.session.post(
                API_LOGIN_PWD,
                data=body,
                timeout=15
            )
            
            print(f"[Login] Status: {response.status_code}")
            
            try:
                result = response.json()
            except json.JSONDecodeError:
                print(f"[Login] Response không phải JSON: {response.text[:200]}")
                return {
                    'success': False,
                    'error': 'Invalid JSON response',
                    'response_text': response.text[:500]
                }
            
            error_code = result.get('error_code') or result.get('error', 0)
            error_message = result.get('error_message') or result.get('message', '')
            
            login_result = {
                'success': error_code == 0,
                'error_code': error_code,
                'error_message': error_message,
                'data': result.get('data', {}),
                'cookies': dict(self.session.cookies),
                'full_response': result
            }
            
            return login_result
                
        except Exception as e:
            print(f"[Login] Lỗi: {e}")
            return {
                'success': False,
                'error': str(e)
            }

# ==================== WORKFLOW CHÍNH ====================

def main_workflow():
    """
    Workflow đăng nhập chính - lấy captcha và đăng nhập.
    """
    print("=" * 60)
    print("ZALO LOGIN - CAPTCHA WORKFLOW")
    print("=" * 60)
    
    # Khởi tạo client
    zalo = ZaloLogin()
    
    # Thông tin đăng nhập
    phone = input("Nhập số điện thoại: ").strip()
    password = input("Nhập mật khẩu: ").strip()
    
    # Bước 1: Kiểm tra captcha requirement
    print("\n1. 🔍 Kiểm tra yêu cầu captcha...")
    captcha_check = zalo.check_need_captcha(phone)
    
    captcha_response = None
    if captcha_check['success'] and captcha_check.get('need_captcha', False):
        print("\n⚠️  CẦN GIẢI CAPTCHA ĐỂ TIẾP TỤC")
        
        # Bước 2: Lấy captcha challenge
        print("\n2. 🛡️ Lấy captcha challenge...")
        captcha_info = zalo.get_captcha_from_browser_method()
        
        if captcha_info['success']:
            # Bước 3: Giải captcha tương tác
            print("\n3. 🔢 Giải captcha...")
            captcha_response = zalo.solve_captcha_interactive(captcha_info)
        else:
            print("   ❌ Không thể lấy captcha, thử đăng nhập không captcha...")
    else:
        print("✅ Không cần captcha, có thể tiếp tục đăng nhập")
    
    # Bước 4: Đăng nhập
    print("\n4. 🔐 Thực hiện đăng nhập...")
    login_result = zalo.login_with_password(phone, password, captcha_response)
    
    # Nếu lỗi session, thử lại với session mới
    if not login_result['success'] and login_result.get('error_code') == -1003:
        print("\n🔄 Session hết hạn, thử lại với session mới...")
        zalo = ZaloLogin()  # Tạo session mới
        login_result = zalo.login_with_password(phone, password, captcha_response)
    
    # Bước 5: Hiển thị kết quả
    print_login_result(login_result)
    
    return login_result

def print_login_result(result):
    """In kết quả đăng nhập."""
    print("\n" + "=" * 50)
    print("KẾT QUẢ ĐĂNG NHẬP")
    print("=" * 50)
    
    if result['success']:
        print("🎉 ĐĂNG NHẬP THÀNH CÔNG!")
        
        user_data = result.get('data', {})
        if user_data:
            user_id = user_data.get('userId') or user_data.get('user_id')
            display_name = user_data.get('displayName') or user_data.get('display_name')
            if user_id:
                print(f"   👤 User ID: {user_id}")
            if display_name:
                print(f"   📛 Tên hiển thị: {display_name}")
        
        # Kiểm tra cookies
        important_cookies = ['zpsid', 'zalo_id', 'zlogin_session']
        found_cookies = [c for c in important_cookies if c in result.get('cookies', {})]
        print(f"   🍪 Cookies: {found_cookies}")
        
    else:
        print(f"❌ Đăng nhập thất bại!")
        error_code = result.get('error_code')
        error_message = result.get('error_message')
        
        print(f"   Mã lỗi: {error_code}")
        print(f"   Thông báo: {error_message}")
        
        # Phân tích lỗi
        if error_code == -1003:
            print("   💡 Gợi ý: Session hết hạn, thử lại")
        elif error_code == 10:
            print("   💡 Gợi ý: Sai mật khẩu")
        elif error_code == 216:
            print("   💡 Gợi ý: Cần captcha hợp lệ")
        elif error_code == 223:
            print("   💡 Gợi ý: Tài khoản bị khóa tạm thời")

# ==================== MAIN ====================

def main():
    print("=" * 60)
    print("ZALO LOGIN - GET CAPTCHA IMAGE AND TOKEN")
    print("=" * 60)
    
    result = main_workflow()
    
    print("\n" + "=" * 60)
    print("HOÀN THÀNH")
    print("=" * 60)

if __name__ == "__main__":
    main()