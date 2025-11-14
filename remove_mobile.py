import csv
from pathlib import Path

INPUT = Path("database/list_phones/listphones.csv")
OUTPUT = Path("database/list_phones/listphones_clean.csv")


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    if phone.startswith("0"):
        return "84" + phone[1:]
    return phone


def clean_csv():
    rows = []

    with INPUT.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)

        # Fieldnames mới – bỏ status
        fieldnames = [fn for fn in reader.fieldnames if fn != "status"]

        for row in reader:
            # xoá key status nếu tồn tại
            row.pop("status", None)

            # xử lý mobile
            mobile = row.get("mobile") or ""
            row["mobile"] = normalize_phone(mobile)

            rows.append(row)

    # Ghi file sạch
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"🎉 DONE! File sạch được lưu tại: {OUTPUT}")


if __name__ == "__main__":
    clean_csv()
