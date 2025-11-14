# main.py
# -*- coding: utf-8 -*-
import json
import time
from pathlib import Path

from solve_captcha import solve_zalo_captcha
from utils import dict_to_cookie_string, pretty_print, save_json, save_ndjson
from zalo_api_capturer import ZaloAPICapturer
from zalo_crypto import ZaloCrypto
from zalo_search_api import ZaloClient
OUTPUT_DIR = Path("./zalo_output")
OUTPUT_DIR.mkdir(exist_ok=True)
list_phones = [
    "84902598948",
    "84913122373",
    "84898453278",
    "84913291442",
    "84914297986",
    "84931258867",
    "84906358895",
    "84778951299",
    "84768872610",
    "84946005002",
    "84989200689",
    "84337725686",
    "84903156842",
    "84979712349",
    "84837307333",
    "84373492225",
    "84353595515",
    "84904129992",
    "84587266061",
    "84912240880",
    "84937707115",
    "84944691010",
    "84902671237",
    "84903442958",
    "84918458853",
    "84708918860",
    "84989702611",
    "84327815158",
    "84902282598"
]
def run_friend_apis(client: ZaloClient, phones: list[str]):
    print("\n=== GỌI API FRIEND ===")
    print("SECRET_KEY_B64:", client.secret_key_b64)

    if not phones:
        print("⚠️ Không có số để query.")
        return

    try:
        for phone in phones:
            print(f"\n📞 Query: {phone}")
            data = client.getUserByPhone(phone)
            pretty_print("Kết quả", data)

            record = data.get("result") or data.get("data") or {}
            if record:
                record["phone"] = phone
                save_ndjson(record, "friend_profiles.ndjson", mode="a")

    except Exception as e:
        print(f"❌ Lỗi khi gọi API: {e}")

# ================== LOGIN + CAPTCHA ==================
def login_with_retry(
    capturer: ZaloAPICapturer,
    phone: str,
    password: str,
    captcha_api_key: str,
    max_retry: int = 2,
):
    """
    Thử login + solve captcha:
        - Nếu solve captcha tự động OK → tiếp tục
        - Nếu solve fail → cho user thao tác tay
        - Nếu lỗi bất ngờ → retry tối đa max_retry lần
    """
    for attempt in range(1, max_retry + 1):
        print(f"\n🔄 Attempt {attempt}/{max_retry}")

        result = login_and_solve_captcha(
            capturer=capturer,
            phone=phone,
            password=password,
            captcha_api_key=captcha_api_key,
        )

        if result == "SUCCESS":
            print("✅ Login + captcha OK!")
            return True

        # ============================
        # ❌ Solve captcha FAIL
        # → Cho người dùng thao tác tay
        # ============================
        if result == "CLICK_FAIL":
            print("⚠️ Không click được captcha. Thử lại sau 3s...")
            continue
            
        if result in ("SOLVE_FAIL", "NO_INFO_CAPTCHA", "CLICK_FAIL"):
            print("⚠️ Không click được captcha. Thử lại sau 3s...")
            continue

        # ============================
        # ❌ Lỗi bất ngờ
        # → Chờ và retry
        # ============================
        if result == "ERROR":
            print("⚠️ Lỗi bất ngờ, thử lại sau 3s...")
            time.sleep(3)
            continue

    # ============================
    # ❌ Hết retry
    # ============================
    print("❌ Login thất bại sau khi thử nhiều lần.")
    return False

def login_and_solve_captcha(
    capturer: ZaloAPICapturer,
    phone: str,
    password: str,
    captcha_api_key: str,
) -> str:
    """
    Thực hiện login + giải captcha + click captcha.

    Return codes:
        - "SUCCESS"          : thành công
        - "NO_INFO_CAPTCHA"  : không lấy được info captcha khi login
        - "SOLVE_FAIL"       : giải captcha lỗi
        - "CLICK_FAIL"       : click captcha lỗi
        - "ERROR"            : exception khác
    """

    try:
        # 1) Login lấy info captcha
        info_captcha_result = capturer.login_with_password(phone, password)
        if not info_captcha_result:
            print("❌ Lỗi khi đăng nhập (không nhận được info captcha).")
            return "NO_INFO_CAPTCHA"

        print("info_captcha_result:", info_captcha_result)

        # 2) Gửi sang anticaptcha.top solve
        solved_captcha_result = solve_zalo_captcha(
            api_key=captcha_api_key,
            image_base64_or_url=info_captcha_result["image_url"],
            instructions=info_captcha_result["question"],
            click_mode="zalo2",
            poll_interval=5,
            timeout=120,
        )
        print("Kết quả giải captcha:", solved_captcha_result)

        if not solved_captcha_result:
            print("❌ Không giải được captcha.")
            return "SOLVE_FAIL"

        # 3) Click vào captcha
        print("🖱️ Đang thực hiện click captcha...")
        click_success = capturer.click_captcha_tiles(solved_captcha_result)
        if not click_success:
            print("❌ Lỗi khi xử lý captcha (click thất bại).")
            return "CLICK_FAIL"

        print("✅ Đã xử lý captcha thành công, chờ trang confirm login...")
        time.sleep(5)
        return "SUCCESS"

    except Exception as e:
        print(f"❌ Exception trong login_and_solve_captcha: {e}")
        import traceback
        traceback.print_exc()
        return "ERROR"

# ================== GIẢI MÃ LOGIN_INFO & BUILD CLIENT ==================


def decrypt_login_data(login_info: dict):
    """
    Nhận login_info từ capturer, giải mã encrypted_data,
    trả về:
      - cookies_dict
      - secret_key_b64 (zpw_enk)
      - zpw_ver, zpw_type
      - zcid, zcid_ext
    """
    zcid = login_info.get("zcid")
    zcid_ext = login_info.get("zcid_ext")
    cookies_dict = login_info.get("cookies", {}) or {}
    encrypted_data = login_info.get("encrypted_data")

    if not encrypted_data:
        print("⚠️ Không có encrypted_data trong login_info → bỏ qua giải mã.")
        return cookies_dict, None, None, None, zcid, zcid_ext

    print("🧩 Đang giải mã encrypted_data bằng zcid & zcid_ext...")
    decrypted_data = ZaloCrypto.decrypt_with_zcid(
        encrypted_b64=encrypted_data,
        zcid=zcid,
        zcid_ext=zcid_ext,
    )

    if isinstance(decrypted_data, dict):
        config_from_decrypted = decrypted_data
    else:
        try:
            config_from_decrypted = json.loads(decrypted_data)
        except Exception:
            config_from_decrypted = {}

    data_section = (config_from_decrypted or {}).get("data", {}) or {}

    secret_key_b64 = data_section.get("zpw_enk")
    zpw_ver = str(data_section.get("zpw_ver", "670"))
    zpw_type = str(data_section.get("zpw_type", "30"))

    return cookies_dict, secret_key_b64, zpw_ver, zpw_type, zcid, zcid_ext


def build_zalo_client_from_login(login_info: dict) -> ZaloClient | None:
    """
    Từ login_info → decrypt → build ZaloClient.
    """
    (
        cookies_dict,
        secret_key_b64,
        zpw_ver,
        zpw_type,
        _zcid,
        _zcid_ext,
    ) = decrypt_login_data(login_info)

    if not secret_key_b64:
        print("❌ Không tìm thấy zpw_enk → không tạo được ZaloClient.")
        return None

    dynamic_cookie_string = dict_to_cookie_string(cookies_dict)
    if not dynamic_cookie_string:
        print("❌ Không có cookies Selenium → không gọi được API friend.")
        return None

    pretty_print("🍪 COOKIE_STRING runtime", dynamic_cookie_string)

    client = ZaloClient(
        secret_key_b64=secret_key_b64,
        cookie_string=dynamic_cookie_string,
        friend_domain="https://tt-friend-wpa.chat.zalo.me",
        zpw_ver=zpw_ver,
        zpw_type=zpw_type,
    )
    return client


# ================== MAIN FLOW ==================
def main():
    print("🤖 ZALO FLOW – LOGIN (Selenium) → DECRYPT → CALL FRIEND APIs")
    print("=" * 80)

    PHONE = "0923540924"
    PASSWORD = "Signethanoi123@"
    CAPTCHA_API_KEY = "c95a3a78034782856d1ca3f4e221afc3"

    capturer = ZaloAPICapturer(headless=False)

    while True:
        try:
            # 1) LOGIN (tự solve captcha → nếu fail thì manual → retry 2 lần)
            ok = login_with_retry(
                capturer,
                phone=PHONE,
                password=PASSWORD,
                captcha_api_key=CAPTCHA_API_KEY,
                max_retry=5
            )
            print("ok:", ok)
            if not ok:
                print("❌ Login thất bại hoàn toàn. Dừng.")
                return

            # 2) Lấy login info
            login_info = capturer.capture_login_info()
            if not login_info:
                print("❌ Không lấy được login_info từ Zalo.")
                return

            # 3) Build client
            client = build_zalo_client_from_login(login_info)
            if not client:
                print("❌ Không tạo được ZaloClient từ login_info.")
                return

            # 4) Gọi API bạn bè
            run_friend_apis(client, list_phones)

            print("\n🎉 FLOW KẾT THÚC – XONG!")
            time.sleep(3)
            capturer.logout()
            time.sleep(3)

        except Exception as e:
            print(f"❌ Lỗi trong main(): {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
    print("\n\n🎉 FLOW KẾT THÚC – XONG!")
