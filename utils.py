# ================== UTILS CƠ BẢN ==================
import json
from pathlib import Path
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

def save_ndjson(record, filename: str, mode: str = "a"):
    """
    Lưu 1 record (dict) hoặc list[dict] thành NDJSON.
    - Nếu là dict → ghi 1 dòng
    - Nếu là list → ghi nhiều dòng
    """
    path = OUTPUT_DIR / filename

    with path.open(mode, encoding="utf-8") as f:
        if isinstance(record, dict):
            # Ghi 1 dòng
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        elif isinstance(record, list):
            # Ghi nhiều dòng
            for rec in record:
                if isinstance(rec, dict):
                    f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        else:
            print("⚠️ record không phải dict hoặc list — bỏ qua:", record)

    print(f"💾 Đã ghi NDJSON vào: {path}")

