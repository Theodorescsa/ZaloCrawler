import pandas as pd

csv_path = "contacts_selected.csv"         # file csv của bạn
sh_path = "import_contacts.sh"

df = pd.read_csv(csv_path)

lines = []
lines.append("#!/system/bin/sh")
lines.append("su")  # vào root trong shell

# --- XÓA TẤT CẢ CONTACT CŨ ---
lines.append('echo "=== XÓA TOÀN BỘ CONTACT CŨ ==="')
lines.append('content delete --uri content://com.android.contacts/raw_contacts')
lines.append('echo "=== ĐÃ XÓA XONG, BẮT ĐẦU IMPORT MỚI ==="')

for _, row in df.iterrows():
    name = str(row.get("name", "")).strip()
    mobile = str(row.get("mobile", "")).strip()

    # skip nếu không có số
    if not mobile or mobile.lower() == "nan":
        continue

    # chuẩn hóa 84 -> 0
    if mobile.startswith("84"):
        mobile = "0" + mobile[2:]

    # escape dấu " trong tên để không vỡ chuỗi shell
    safe_name = name.replace('"', '\\"')

    lines.append("")
    lines.append(f'echo "=== Tạo contact: {safe_name} - {mobile} ==="')

    # 1) Tạo raw_contact (account local)
    lines.append(
        'RAW_ID=$(content insert '
        '--uri content://com.android.contacts/raw_contacts '
        '--bind account_type:s:local '
        '--bind account_name:s:phone '
        '| sed -n \'s/Inserted row id: //p\')'
    )

    # 2) Thêm tên
    lines.append(
        'content insert --uri content://com.android.contacts/data '
        '--bind raw_contact_id:i:$RAW_ID '
        '--bind mimetype:s:vnd.android.cursor.item/name '
        f'--bind data1:s:"{safe_name}"'
    )

    # 3) Thêm số (type=2 = mobile)
    lines.append(
        'content insert --uri content://com.android.contacts/data '
        '--bind raw_contact_id:i:$RAW_ID '
        '--bind mimetype:s:vnd.android.cursor.item/phone_v2 '
        '--bind data2:i:2 '
        f'--bind data1:s:"{mobile}"'
    )

with open(sh_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("✅ Đã tạo file shell:", sh_path)
