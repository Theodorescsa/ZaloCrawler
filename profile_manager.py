import os
import shutil
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
from solve_captcha import solve_zalo_captcha
from zalo_api_capturer import ZaloAPICapturer
class ProfileManager:
    def __init__(self, base_dir="browser_profiles"):
        # Tạo thư mục gốc chứa các profile nếu chưa có
        self.base_dir = os.path.join(os.getcwd(), base_dir)
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_profile_path(self, profile_id):
        """Tạo đường dẫn tuyệt đối cho từng profile_id"""
        return os.path.join(self.base_dir, profile_id)

    def delete_profile(self, profile_id):
        """Xóa sạch dữ liệu của 1 profile nếu muốn reset"""
        path = self.get_profile_path(profile_id)
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"🗑️ Đã xóa data của profile: {profile_id}")
            except Exception as e:
                print(f"❌ Không xóa được profile {profile_id}: {e}")
                


# ==============================================================================
# HÀM CHẠY 1 PROFILE
# ==============================================================================

def run_single_account(account_config):
    """
    account_config = {
        "id": "acc_01",
        "phone": "098xxxxxxx",
        "pass": "password123",
        "port": 9222,
        "headless": False,
        "window_pos": (0, 0),  # (x, y)
        "window_size": (600, 800)
    }
    """
    profile_id = account_config["id"]
    port = account_config.get("port", 9222)
    
    # 1. Setup đường dẫn lưu data
    manager = ProfileManager()
    user_data_path = manager.get_profile_path(profile_id)
    
    print(f"🚀 Đang khởi động profile: {profile_id}")
    print(f"📂 Data lưu tại: {user_data_path}")
    print(f"🔌 Debug Port: {port}")

    # 2. Cấu hình Chrome
    # Lưu ý: Khi dùng user_data_dir riêng, profile_directory thường để mặc định là "Default"
    # Class ZaloAPICapturer của bạn cần hỗ trợ nhận các tham số window (hoặc ta patch vào option)
    
    try:
        capturer = ZaloAPICapturer(
            headless=account_config.get("headless", False),
            remote_port=port,
            user_data_dir=user_data_path,
            profile_name="Default" # Luôn là Default trong folder riêng
        )

        # 3. Tùy chỉnh vị trí cửa sổ (Giống Morelogin sắp xếp)
        if not account_config.get("headless", False) and capturer.driver:
            x, y = account_config.get("window_pos", (0, 0))
            w, h = account_config.get("window_size", (1000, 800))
            capturer.driver.set_window_position(x, y)
            capturer.driver.set_window_size(w, h)

        # 4. Logic đăng nhập (Code cũ của bạn)
        API_KEY_CAPTCHA = "YOUR_API_KEY" # Điền API giải captcha của bạn
        
        # Kiểm tra xem đã login chưa (có cookies cũ không)
        capturer.driver.get("https://chat.zalo.me")
        
        # -- Đợi check login --
        # Nếu chưa login thì mới chạy luồng login
        # (Ở đây viết demo gọi hàm login luôn)
        
        print(f"[{profile_id}] Bắt đầu luồng đăng nhập...")
        
        # Gọi hàm login main cũ của bạn (đã sửa lại để nhận object capturer)
        # Lưu ý: Bạn cần tách hàm logic xử lý ra khỏi hàm main để gọi lại cho gọn
        zalo_login_process(capturer, account_config["phone"], account_config["pass"], API_KEY_CAPTCHA)

        # Giữ browser mở 1 lúc hoặc làm việc gì đó
        # time.sleep(1000) 
        
    except Exception as e:
        print(f"❌ Lỗi profile {profile_id}: {e}")
    finally:
        # Nếu muốn đóng browser sau khi chạy xong thì uncomment
        # capturer.close()
        pass

# ==============================================================================
# HÀM LOGIC XỬ LÝ (Tách từ zalo_login_main cũ)
# ==============================================================================
def zalo_login_process(capturer, PHONE, PASSWORD, API_KEY):
    """Hàm này chứa logic nghiệp vụ: Login -> Giải Captcha -> Lấy Token"""
    try:
        # Thử login
        info_captcha = capturer.login_with_password(PHONE, PASSWORD)
        
        # Nếu có captcha thì giải
        if info_captcha and info_captcha.get('exists'):
            print("🧩 Phát hiện captcha, đang giải...")
            solved_result = solve_zalo_captcha(
                api_key=API_KEY,
                image_base64_or_url=info_captcha["image_url"],
                instructions=info_captcha["question"],
                click_mode="zalo2"
            )
            if solved_result:
                capturer.click_captcha_tiles(solved_result)
        
        # Chờ bắt hook data
        data = capturer.capture_login_info()
        
        # Lưu file riêng cho profile này
        filename = f"zalo_data_{capturer.remote_port}.json"
        capturer.save_to_file(data, filename)
        
    except Exception as e:
        print(f"Lỗi logic: {e}")

def get_screen_resolution():
    """
    Hàm lấy độ phân giải hiển thị thực tế (đã tính Scale của Windows).
    Ví dụ: Màn 1920x1080 nhưng Scale 125% -> Trả về 1536x864
    Đây là con số chính xác để set vị trí cửa sổ.
    """
    try:
        root = tk.Tk()
        root.withdraw() # Ẩn cửa sổ tk đi
        width = root.winfo_screenwidth()
        height = root.winfo_screenheight()
        root.destroy()
        return width, height
    except Exception:
        # Fallback nếu lỗi (ít khi xảy ra)
        return 1920, 1080

def apply_auto_grid(accounts, rows=4, cols=4):
    """
    Tự động chia lưới dựa trên độ phân giải thật của máy
    """
    # 1. Tự động lấy độ phân giải
    screen_w, screen_h = get_screen_resolution()
    
    # Cấu hình Taskbar (thường là 40px)
    TASKBAR_HEIGHT = 40
    usable_height = screen_h - TASKBAR_HEIGHT
    
    # Khoảng cách an toàn để tránh dính viền (Gap)
    GAP_X = 10 
    GAP_Y = 0

    print(f"\n{'='*60}")
    print(f"🖥️  PHÁT HIỆN MÀN HÌNH CỦA BẠN: {screen_w} x {screen_h}")
    print(f"📐  Layout: {rows} Hàng x {cols} Cột")
    
    # --- CHECK QUAN TRỌNG: Chrome Minimum Width ---
    # Chrome không thể thu nhỏ hơn ~400px - 500px (tùy phiên bản/extension)
    expected_width = (screen_w / cols) - GAP_X
    print(f"ℹ️  Chiều rộng dự kiến mỗi cửa sổ: {int(expected_width)}px")
    
    if expected_width < 400:
        print(f"⚠️  CẢNH BÁO: Chiều rộng {int(expected_width)}px QUÁ NHỎ!")
        print(f"    Chrome sẽ tự động phình to ra (~500px) gây chèn lấn.")
        print(f"    👉 KHUYẾN NGHỊ: Giảm số cột xuống còn {int(screen_w/500)} hoặc {int(screen_w/450)}.")
    else:
        print(f"✅  Kích thước hợp lý. Cửa sổ sẽ hiển thị đẹp.")
    print(f"{'='*60}")

    # 2. Tính toán vị trí
    for index, acc in enumerate(accounts):
        grid_pos = index % (rows * cols)
        row_idx = grid_pos // cols
        col_idx = grid_pos % cols

        # Tính toán tọa độ (Logic chia dư chuẩn xác)
        x_start = int(col_idx * screen_w / cols)
        x_next = int((col_idx + 1) * screen_w / cols)
        
        y_start = int(row_idx * usable_height / rows)
        y_next = int((row_idx + 1) * usable_height / rows)

        # Trừ hao gap
        final_w = (x_next - x_start) - GAP_X
        final_h = (y_next - y_start) - GAP_Y
        
        # Cập nhật config
        acc["window_pos"] = (x_start, y_start)
        acc["window_size"] = (final_w, final_h)
        
        # In ra để debug
        # print(f"[{acc['id']}] Pos: {x_start},{y_start} Size: {final_w}x{final_h}")

    return accounts

# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == "__main__":
    # 1. Tạo data giả lập (hoặc load từ database của bạn)
    raw_accounts = []
    for i in range(20):
        raw_accounts.append({
            "id": f"acc_{i+1:02d}", 
            "phone": "098xxx", 
            "pass": "xxx", 
            "port": 9000+i,
            "headless": False
        })

    # 2. Áp dụng Layout tự động (Không cần điền screen_res thủ công nữa)
    # Thử chỉnh số cột (cols) thấp xuống nếu màn hình bạn nhỏ
    accounts_ready = apply_auto_grid(raw_accounts, rows=4, cols=4)

    # 3. Chạy
    with ThreadPoolExecutor(max_workers=5) as executor: # Chỉnh max_workers tùy máy mạnh/yếu
        executor.map(run_single_account, accounts_ready)