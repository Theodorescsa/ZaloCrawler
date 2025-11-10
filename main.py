# main.py
# -*- coding: utf-8 -*-
import json
import time
from pathlib import Path

from zalo_login import ZaloAPICapturer
from zalo_crypto import ZaloCrypto
from zalo_search_api import ZaloClient  # dùng class thay vì global module


OUTPUT_DIR = Path("./zalo_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def dict_to_cookie_string(cookies: dict) -> str:
    """
    Chuyển dict cookies Selenium -> chuỗi Cookie header:
    {"a": "1", "b": "2"} -> "a=1; b=2"
    """
    parts = []
    for k, v in cookies.items():
        if v is None:
            continue
        parts.append(f"{k}={v}")
    return "; ".join(parts)


def pretty_print(title: str, data):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(data)
    print("=" * 80 + "\n")


def save_json(data, filename: str):
    path = OUTPUT_DIR / filename
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"💾 Đã lưu file: {path}")


def run_friend_apis(client: ZaloClient):
    """
    Hỏi input ở CLI để gọi thử getUserByPhone / getMultiUsersByPhones
    dùng ZaloClient (đã truyền sẵn SECRET_KEY_B64 = zpw_enk + COOKIE runtime).
    """
    print("\n=== GỌI CÁC API FRIEND (tt-friend-wpa.chat.zalo.me) ===")
    print("SECRET_KEY_B64 (zpw_enk) hiện tại:", client.secret_key_b64)

    # 1) Gọi getUserByPhone
    phone = input("Nhập 1 số điện thoại để gọi getUserByPhone (bỏ trống để skip): ").strip()
    if phone:
        try:
            data = client.getUserByPhone(phone)
            pretty_print(f"📱 Kết quả getUserByPhone({phone})", data)
            save_json(data, f"friend_profile_{phone}.json")
        except Exception as e:
            print(f"❌ Lỗi khi gọi getUserByPhone: {e}")

    # 2) Gọi getMultiUsersByPhones
    phones_raw = input("Nhập list số điện thoại (cách nhau bởi dấu phẩy) để gọi getMultiUsersByPhones (bỏ trống để skip): ").strip()
    if phones_raw:
        phones = [p.strip() for p in phones_raw.split(",") if p.strip()]
        if phones:
            try:
                data_multi = client.getMultiUsersByPhones(phones)
                pretty_print(f"👥 Kết quả getMultiUsersByPhones({phones})", data_multi)
                save_json(data_multi, "friend_multi_profiles.json")
            except Exception as e:
                print(f"❌ Lỗi khi gọi getMultiUsersByPhones: {e}")


def main():
    print("🤖 ZALO FLOW – LOGIN (Selenium) → DECRYPT → CALL FRIEND APIs")
    print("=" * 80)

    capturer = ZaloAPICapturer(headless=False)

    try:
        # 1) Login thủ công
        if not capturer.login_manually():
            print("❌ Không thực hiện được bước đăng nhập.")
            return

        # 2) Bắt thông tin login (zcid, zcid_ext, cookies, encrypted_data...)
        login_info = capturer.capture_login_info()
        if not login_info:
            print("❌ Không lấy được login_info từ Zalo.")
            return

        # ---- Unpack các trường quan trọng ----
        zcid = login_info.get("zcid")
        zcid_ext = login_info.get("zcid_ext")
        cookies_dict = login_info.get("cookies", {}) or {}
        api_response = login_info.get("api_response", {}) or {}
        encrypted_data = login_info.get("encrypted_data")

        pretty_print("🔑 THÔNG TIN CƠ BẢN TỪ LOGIN", {
            "zcid": zcid,
            "zcid_ext": zcid_ext,
            "has_encrypted_data": encrypted_data is not None,
            "cookie_count": len(cookies_dict),
            "api_error_code": api_response.get("error_code"),
        })

        # Lưu raw login_info (debug)
        save_json(login_info, "zalo_login_raw.json")

        # 3) Giải mã encrypted_data bằng ZaloCrypto (zcid + zcid_ext)
        decrypted_data = None
        config_from_decrypted = {}

        if encrypted_data:
            print("🧩 Đang giải mã encrypted_data bằng zcid & zcid_ext...")
            decrypted_data = ZaloCrypto.decrypt_with_zcid(
                encrypted_b64=encrypted_data,
                zcid=zcid,
                zcid_ext=zcid_ext,
            )

            # Lưu & in ra cho debug
            pretty_print("✅ DỮ LIỆU SAU GIẢI MÃ getLoginInfo", decrypted_data)
            save_json(decrypted_data, "zalo_login_decrypted.json")

            # decrypted_data có thể là dict hoặc string JSON
            if isinstance(decrypted_data, dict):
                config_from_decrypted = decrypted_data
            else:
                try:
                    config_from_decrypted = json.loads(decrypted_data)
                except Exception:
                    config_from_decrypted = {}
        else:
            print("⚠️ api_response không có trường 'data', bỏ qua giải mã.")

        # 4) Lấy SECRET_KEY_B64 (zpw_enk) + zpw_ver, zpw_type từ decrypted_data
        data_section = (config_from_decrypted or {}).get("data", {}) or {}

        secret_key_b64 = data_section.get("zpw_enk")
        zpw_ver = str(data_section.get("zpw_ver", "670"))
        zpw_type = str(data_section.get("zpw_type", "30"))

        if not secret_key_b64:
            print("❌ Không tìm thấy zpw_enk trong decrypted_data['data'] → không tạo được ZaloClient.")
            return

        # 5) Build COOKIE_STRING từ cookies runtime
        dynamic_cookie_string = dict_to_cookie_string(cookies_dict)
        if not dynamic_cookie_string:
            print("❌ Không có cookies Selenium → không gọi được API friend.")
            return

        pretty_print("🍪 COOKIE_STRING runtime", dynamic_cookie_string)

        # 6) Tạo ZaloClient với secret_key_b64 = zpw_enk + cookie runtime
        client = ZaloClient(
            secret_key_b64=secret_key_b64,
            cookie_string=dynamic_cookie_string,
            friend_domain="https://tt-friend-wpa.chat.zalo.me",
            zpw_ver=zpw_ver,
            zpw_type=zpw_type,
        )

        # 7) Gọi thử các API friend
        run_friend_apis(client)

        print("\n🎉 FLOW KẾT THÚC – XONG!")

    except Exception as e:
        print(f"❌ Lỗi trong main(): {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("⏰ Nhấn Enter để đóng trình duyệt...")
        capturer.close()


if __name__ == "__main__":
    main()

    print("\n\n🎉 FLOW KẾT THÚC – XONG!")