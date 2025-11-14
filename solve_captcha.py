import time
import base64
import requests


def encode_image_to_base64(image_path: str) -> str:
    """
    Đọc file ảnh và trả về chuỗi base64 (dạng string, KHÔNG kèm prefix data:image/...).
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

import time
import requests


def solve_zalo_captcha(
    api_key: str,
    image_base64_or_url: str,
    instructions: str = "Chọn tất cả hình ảnh có: con mèo",
    click_mode: str = "zalo2",  # "zalo" => tọa độ, "zalo2" => thứ tự ảnh
    poll_interval: int = 5,     # số giây chờ giữa mỗi lần hỏi kết quả
    timeout: int = 120          # tối đa chờ bao nhiêu giây
):
    """
    Trả về:
        - KẾT QUẢ captcha (request field từ anticaptcha.top) nếu thành công
        - None nếu có lỗi / timeout / task fail
    """

    # 1. Tạo task
    create_url = "https://anticaptcha.top/in.php"
    create_payload = {
        "key": api_key,
        "method": "base64",
        "textinstructions": instructions,
        "click": click_mode,
        "body": image_base64_or_url,  # base64 ảnh hoặc URL ảnh
        "json": 1,
    }

    try:
        resp = requests.post(create_url, json=create_payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Lỗi khi tạo task captcha (network/error): {e}")
        return None

    if data.get("status") != 1:
        print(f"❌ Tạo task captcha thất bại: {data}")
        return None

    task_id = data.get("request")
    if not task_id:
        print(f"❌ Không nhận được task_id hợp lệ: {data}")
        return None

    # 2. Poll kết quả
    result_url = "https://anticaptcha.top/res.php"
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            print("⏰ Hết thời gian chờ kết quả captcha")
            return None

        params = {
            "key": api_key,
            "id": task_id,
            "json": 1,
        }

        try:
            r = requests.get(result_url, params=params, timeout=30)
            r.raise_for_status()
            res_data = r.json()
        except Exception as e:
            print(f"❌ Lỗi khi lấy kết quả captcha (network/error): {e}")
            return None

        status = res_data.get("status")
        req_val = res_data.get("request")

        if status == 0 and req_val == "CAPCHA_NOT_READY":
            # đang xử lý, chờ thêm
            time.sleep(poll_interval)
            continue
        elif status == 1:
            # thành công → trả về phần "request"
            return req_val
        else:
            # lỗi khác (BAD KEY, ERROR_CAPTCHA_UNSOLVABLE, ...)
            print(f"❌ Lỗi khi lấy kết quả captcha: {res_data}")
            return None


if __name__ == "__main__":
    API_KEY = "6faef718e1c982aa9a263efb748c95e7"

    # Cách 1: dùng file ảnh local
    # img_b64 = encode_image_to_base64("zalo_captcha.png")

    # Cách 2: hoặc dùng URL ảnh trực tiếp
    # img_b64 = "https://example.com/path/to/captcha.png"

    result = solve_zalo_captcha(
        api_key=API_KEY,
        image_base64_or_url="https://zcaptcha.zdn.vn/365b6fb051e4b8bae1f5",
        instructions="Chọn tất cả hình ảnh có: máy bay",
        click_mode="zalo2",   # hoặc "zalo"
        poll_interval=5,
        timeout=120
    )

    print("Kết quả giải captcha:", result)
