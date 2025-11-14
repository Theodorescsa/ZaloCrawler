# ================== UTILS CƠ BẢN ==================
import json
from pathlib import Path
import csv
PHONE_CSV_PATH = Path("database/list_phones/listphones.csv")
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


def load_phones_batch(limit: int = 29):
    """
    Đọc file CSV, lấy tối đa `limit` số chưa có status = done.
    Trả về:
      - rows: list toàn bộ dòng (để tí nữa ghi lại)
      - indices: list index các dòng được chọn
      - phones: list số điện thoại tương ứng
    """
    rows: list[dict] = []

    with PHONE_CSV_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    pending_indices: list[int] = []
    phones: list[str] = []

    for idx, row in enumerate(rows):
        status = (row.get("status") or "").strip().lower()
        # chỉ xử lý những dòng chưa done
        if status == "done":
            continue

        phone = (row.get("phone") or row.get("mobile") or "").strip()
        if not phone:
            continue

        phones.append(phone)
        pending_indices.append(idx)

        if len(phones) >= limit:
            break

    return rows, pending_indices, phones

def save_status_back_to_csv(rows: list[dict]):
    """
    Ghi lại toàn bộ rows về file CSV, giữ header cũ.
    """
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    # Nếu file cũ chưa có cột status thì thêm vào
    if "status" not in fieldnames:
        fieldnames.append("status")

    with PHONE_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
