import time
import base64
import requests


def encode_image_to_base64(image_path: str) -> str:
    """
    Đọc file ảnh và trả về chuỗi base64 (dạng string, KHÔNG kèm prefix data:image/...).
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def solve_zalo_captcha(
    api_key: str,
    image_base64_or_url: str,
    instructions: str = "Chọn tất cả hình ảnh có: con mèo",
    click_mode: str = "zalo2",  # "zalo" => tọa độ, "zalo2" => thứ tự ảnh
    poll_interval: int = 5,     # số giây chờ giữa mỗi lần hỏi kết quả
    timeout: int = 120          # tối đa chờ bao nhiêu giây
):
    """
    Gửi ảnh captcha lên anticaptcha.top và trả về kết quả đã giải.
    
    Return:
        - Nếu click_mode="zalo2": ví dụ "1,2,6,9"
        - Nếu click_mode="zalo": ví dụ "coordinate:x=44,y=32;x=143,y=11"
    """
    # 1. Tạo task
    create_url = "https://anticaptcha.top/in.php"
    create_payload = {
        "key": api_key,
        "method": "base64",
        "textinstructions": instructions,
        "click": click_mode,
        "body": image_base64_or_url,  # base64 ảnh hoặc URL ảnh
        "json": 1
    }

    resp = requests.post(create_url, json=create_payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != 1:
        raise RuntimeError(f"Tạo task thất bại: {data}")

    task_id = data.get("request")
    # print("Created task id:", task_id)

    # 2. Poll kết quả
    result_url = "https://anticaptcha.top/res.php"
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            raise TimeoutError("Hết thời gian chờ kết quả captcha")

        params = {
            "key": api_key,
            "id": task_id,
            "json": 1
        }
        r = requests.get(result_url, params=params, timeout=30)
        r.raise_for_status()
        res_data = r.json()

        status = res_data.get("status")
        if status == 0 and res_data.get("request") == "CAPCHA_NOT_READY":
            # đang xử lý, chờ thêm
            time.sleep(poll_interval)
            continue
        elif status == 1:
            # thành công
            return res_data.get("request")
        else:
            # lỗi khác
            raise RuntimeError(f"Lỗi khi lấy kết quả: {res_data}")

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
