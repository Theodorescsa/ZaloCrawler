import requests
import json
from urllib.parse import urlparse, parse_qs
import time

def simulate_zalo_qr_scan(qr_code_url):
    """
    Giả lập việc quét QR code Zalo từ điện thoại
    """
    # Phân tích QR code URL
    parsed_url = urlparse(qr_code_url)
    query_params = parse_qs(parsed_url.query)
    
    session_id = query_params.get('session_id', [''])[0]
    token = query_params.get('token', [''])[0]
    
    print(f"Session ID: {session_id}")
    print(f"Token: {token}")
    
    # Headers giả lập app Zalo
    headers = {
        'User-Agent': 'Zalo/5.0 (iPhone; iOS 15.0; Scale/3.00)',
        'X-Zalo-Version': '5.0.0',
        'X-Device-Id': 'simulated-device-python-123',
        'X-OS-Type': 'ios',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Data gửi đến server Zalo
    payload = {
        'session_id': session_id,
        'token': token,
        'device_id': 'simulated-device-python-123',
        'device_name': 'Python Simulated Device',
        'platform': 'ios',
        'version': '5.0.0',
        'action': 'confirm_login'
    }
    
    try:
        # Gửi request confirm login (bước quét QR)
        confirm_url = "https://zalo.me/api/device-auth/confirm"
        response = requests.post(
            confirm_url, 
            headers=headers, 
            json=payload,
            timeout=10
        )
        
        print(f"Confirm Response: {response.status_code}")
        print(f"Confirm Data: {response.text}")
        
        if response.status_code == 200:
            return True
        else:
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

# Sử dụng
qr_url = "https://zalo.me/device-auth?session_id=abc123&token=xyz456&version=3"
simulate_zalo_qr_scan(qr_url)