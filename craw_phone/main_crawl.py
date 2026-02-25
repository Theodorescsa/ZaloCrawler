import json
import threading
import time
import random
import csv
import os
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

# Import class ZaloClient
try:
    from zalo_client import ZaloClient
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from zalo_client import ZaloClient

# --- CẤU HÌNH ---
INPUT_FILE = r"phone.txt"
INPUT_ACCOUNTS = "accounts.json"
OUTPUT_FILE = "results.ndjson"
DEFAULT_COOLDOWN = 3600   # 1 tiếng khi bị lỗi nặng (312, -366)

# --- CẤU HÌNH KỊCH BẢN MỚI ---
LIMIT_HOURLY = 26         # Số lượng tối đa trong 1 giờ
LIMIT_DAILY = 129         # Số lượng tối đa trong 1 ngày
LIMIT_COOLDOWN = 3600     # Thời gian nghỉ sau khi đạt giới hạn giờ (1 tiếng)
class AccountWrapper:
    def __init__(self, acc_data, index):
        self.id = index
        self.proxy = acc_data.get('proxy')
        self.client = ZaloClient(
            secret_key_b64=acc_data['secret_key_b64'],
            cookie_string=acc_data['cookie']
        )
        self.is_cooldown = False
        self.cooldown_until = None
        
        # Biến theo dõi kịch bản
        self.hourly_request_count = 0
        self.daily_request_count = 0
        self.last_reset_date = datetime.now().date()

class AccountManager:
    def __init__(self, account_file):
        self.active_queue = Queue()
        self.cooldown_list = [] 
        self.lock = threading.Lock()
        self.load_accounts(account_file)

    def load_accounts(self, filepath):
        try:
            if not os.path.exists(filepath):
                print(f"[ERROR] File account '{filepath}' không tồn tại!")
                exit()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for idx, acc in enumerate(data):
                wrapper = AccountWrapper(acc, idx)
                self.active_queue.put(wrapper)
            print(f"[INIT] Đã load {self.active_queue.qsize()} tài khoản.")
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file account: {e}")
            exit()

    def get_account(self):
        while True:
            try:
                return self.active_queue.get_nowait()
            except Empty:
                pass

            with self.lock:
                now = datetime.now()
                ready_indices = []
                for i, acc in enumerate(self.cooldown_list):
                    if now >= acc.cooldown_until:
                        ready_indices.append(i)
                
                for i in reversed(ready_indices):
                    acc = self.cooldown_list.pop(i)
                    acc.is_cooldown = False
                    acc.cooldown_until = None
                    print(f"♻️ [RESTORE] Account #{acc.id} đã hết thời gian chờ.")
                    self.active_queue.put(acc)

            time.sleep(1)

    def return_account(self, account, cooldown_seconds=0):
        if cooldown_seconds > 0:
            with self.lock:
                account.is_cooldown = True
                account.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
                self.cooldown_list.append(account)
            
            wait_min = int(cooldown_seconds / 60)
            resume_time = account.cooldown_until.strftime("%d/%m %H:%M:%S")
            print(f"🚫 [LIMIT] Account #{account.id} tạm dừng {wait_min} phút (đến {resume_time}).")
        else:
            self.active_queue.put(account)

class ZaloCrawler:
    def __init__(self):
        self.manager = AccountManager(INPUT_ACCOUNTS)
        self.phone_queue = Queue()
        self.file_lock = threading.Lock()
        self.load_phones()

    def load_phones(self):
        if not os.path.exists(INPUT_FILE):
            print(f"[ERROR] File data '{INPUT_FILE}' không tồn tại!")
            return

        print(f"[INIT] Đang đọc file input: {INPUT_FILE}...")
        count = 0
        try:
            if INPUT_FILE.lower().endswith('.csv'):
                with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames and 'mobile' not in reader.fieldnames:
                        print(f"[ERROR] CSV thiếu cột 'mobile'.")
                        return
                    for row in reader:
                        p = row.get('mobile', '').strip()
                        if p:
                            self.phone_queue.put(p)
                            count += 1
            else:
                with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        p = line.strip()
                        if p:
                            self.phone_queue.put(p)
                            count += 1
            print(f"[INIT] Đã nạp {count} số điện thoại.")
        except Exception as e:
            print(f"[ERROR] Lỗi đọc file data: {e}")

    def save_ndjson(self, data):
        with self.file_lock:
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def worker_task(self):
        while True:
            try:
                phone = self.phone_queue.get(timeout=3)
            except Empty:
                break 

            acc_wrapper = self.manager.get_account()
            
            try:
                time.sleep(random.uniform(0.5, 2.0))
                
                proxies = None
                if acc_wrapper.proxy:
                    proxies = {"http": acc_wrapper.proxy, "https": acc_wrapper.proxy}
                
                result = acc_wrapper.client.getUserByPhone(phone, proxies=proxies)
                
                # --- XỬ LÝ KẾT QUẢ ---
                wait_seconds = 0
                error_code = 0
                
                if isinstance(result, dict):
                    error_code = result.get("error_code", 0)

                # TRƯỜNG HỢP 1: LỖI
                if error_code != 0:
                    err_msg = result.get("error_message", "Unknown") if isinstance(result, dict) else str(result)
                    print(f"⚠️ [FAIL] {phone} (Code {error_code}): {err_msg}")

                    if error_code == 312:
                        expire_ts = result.get("data", {}).get("expireTs")
                        if expire_ts:
                            future_ts = expire_ts / 1000
                            now_ts = time.time()
                            wait_seconds = future_ts - now_ts + 60
                            if wait_seconds < 0: wait_seconds = 300 
                        else:
                            wait_seconds = DEFAULT_COOLDOWN 
                    elif error_code in [-366, -30]:
                        wait_seconds = DEFAULT_COOLDOWN
                    
                    self.phone_queue.put(phone)

                # TRƯỜNG HỢP 2: THÀNH CÔNG (error_code == 0)
                else:
                    # Kiểm tra xem có qua ngày mới chưa để reset biến đếm ngày
                    today = datetime.now().date()
                    if acc_wrapper.last_reset_date != today:
                        acc_wrapper.daily_request_count = 0
                        acc_wrapper.hourly_request_count = 0
                        acc_wrapper.last_reset_date = today

                    # 1. Tăng biến đếm thành công
                    acc_wrapper.hourly_request_count += 1
                    acc_wrapper.daily_request_count += 1
                    
                    # 2. Lưu dữ liệu
                    data_save = result.get("data", {})
                    data_save["_phone_input"] = phone 
                    self.save_ndjson(data_save)
                    print(f"✅ [OK] {phone} -> {data_save.get('display_name', 'Unknown')} (Acc #{acc_wrapper.id} - Giờ: {acc_wrapper.hourly_request_count}/{LIMIT_HOURLY} | Ngày: {acc_wrapper.daily_request_count}/{LIMIT_DAILY})")

                    # 3. Kiểm tra Giới hạn Ngày (149 số)
                    if acc_wrapper.daily_request_count >= LIMIT_DAILY:
                        # Tính số giây từ giờ cho đến 00:00:01 của ngày hôm sau
                        now = datetime.now()
                        tomorrow = now + timedelta(days=1)
                        midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 1)
                        wait_seconds = (midnight - now).total_seconds()
                        
                        print(f"🛑 [DAILY MAX] Acc #{acc_wrapper.id} đã quét đủ {LIMIT_DAILY} số/ngày. Nghỉ đến ngày mai.")
                        acc_wrapper.hourly_request_count = 0 # Reset trước để mai chạy tiếp
                        acc_wrapper.daily_request_count = 0
                        acc_wrapper.last_reset_date = tomorrow.date()

                    # 4. Nếu chưa đạt giới hạn Ngày, thì kiểm tra Giới hạn Giờ (26 số)
                    elif acc_wrapper.hourly_request_count >= LIMIT_HOURLY:
                        print(f"🛑 [HOURLY MAX] Acc #{acc_wrapper.id} đã quét đủ {LIMIT_HOURLY} số. Nghỉ {LIMIT_COOLDOWN//60} phút.")
                        wait_seconds = LIMIT_COOLDOWN
                        acc_wrapper.hourly_request_count = 0  # Reset lại mốc theo giờ

                # Trả acc về manager
                self.manager.return_account(acc_wrapper, cooldown_seconds=wait_seconds)

            except Exception as e:
                print(f"❌ [EXCEPTION] {e}")
                self.manager.return_account(acc_wrapper, cooldown_seconds=0)
                self.phone_queue.put(phone) 

            finally:
                self.phone_queue.task_done()

    def run(self):
        total_acc = self.manager.active_queue.qsize()
        if total_acc == 0:
            print("❌ Không có tài khoản nào để chạy!")
            return

        num_workers = min(total_acc, 20)
        
        print(f"📊 Phát hiện {total_acc} tài khoản. Hệ thống sẽ chạy {num_workers} luồng.")
        print("🚀 Bắt đầu chạy crawler...")
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            for _ in range(num_workers):
                executor.submit(self.worker_task)
        
        self.phone_queue.join()
        print("🏁 Đã xử lý xong toàn bộ danh sách.")

if __name__ == "__main__":
    crawler = ZaloCrawler()
    time.sleep(3600)
    crawler.run()