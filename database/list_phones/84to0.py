import pandas as pd

# Nhập file CSV
file_in = "listphones.csv"
file_out = "contacts_selected.csv"

# Chọn khoảng dòng (theo số thứ tự trong file, tính từ 1)
start_row = 19001   # dòng bắt đầu (ví dụ dòng 100)
end_row = 21000     # dòng kết thúc (ví dụ dòng 300)

# Đọc file
df = pd.read_csv(file_in)

# Vì pandas index bắt đầu từ 0 → phải trừ 1
start_idx = start_row - 1
end_idx = end_row - 1

# Lấy đúng các dòng cần xuất
selected = df.loc[start_idx:end_idx].copy()

# Xử lý thay 84 -> 0 trên cột 'mobile'
selected['mobile'] = (
    selected['mobile'].astype(str)
    .str.replace(r'^84', '0', regex=True)
)

# Xuất ra file mới, chỉ gồm header + các dòng đã chọn
selected.to_csv(file_out, index=False)

print("✅ Done! File output:", file_out)
