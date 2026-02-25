import json
import threading
import time
import random
import csv
import os
import logging
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
DEFAULT_COOLDOWN = 3600   # 1 tiếng khi bị lỗi nặng (312, -366, 221)
LIMIT_REQUESTS = 26       # Số lượng request THÀNH CÔNG tối đa trước khi nghỉ
LIMIT_COOLDOWN = 3600     # Thời gian nghỉ sau khi đạt giới hạn (1 tiếng)
LOG_FILE = "crawler.log"

# --- CẤU HÌNH LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
        self.request_count = 0 

class AccountManager:
    def __init__(self, account_file):
        self.active_queue = Queue()
        self.cooldown_list = [] 
        self.lock = threading.Lock()
        self.load_accounts(account_file)

    def load_accounts(self, filepath):
        try:
            if not os.path.exists(filepath):
                logger.error(f"[ERROR] File account '{filepath}' không tồn tại!")
                exit()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for idx, acc in enumerate(data):
                wrapper = AccountWrapper(acc, idx)
                self.active_queue.put(wrapper)
            logger.info(f"[INIT] Đã load {self.active_queue.qsize()} tài khoản.")
        except Exception as e:
            logger.error(f"[ERROR] Lỗi đọc file account: {e}")
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
                    logger.info(f"♻️ [RESTORE] Account #{acc.id} đã hết thời gian chờ.")
                    self.active_queue.put(acc)

            time.sleep(1)

    def return_account(self, account, cooldown_seconds=0):
        if cooldown_seconds > 0:
            with self.lock:
                account.is_cooldown = True
                account.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
                self.cooldown_list.append(account)
            
            wait_min = int(cooldown_seconds / 60)
            resume_time = account.cooldown_until.strftime("%H:%M:%S")
            logger.warning(f"🚫 [LIMIT] Account #{account.id} tạm dừng {wait_min} phút (đến {resume_time}).")
        else:
            self.active_queue.put(account)

class ZaloCrawler:
    def __init__(self):
        self.manager = AccountManager(INPUT_ACCOUNTS)
        self.phone_queue = Queue()
        self.file_lock = threading.Lock()
        self.done_phones = self.load_done_phones() # Load danh sách đã chạy
        self.load_phones()

    def load_done_phones(self):
        """Đọc file kết quả để lấy các số điện thoại đã crawl thành công."""
        done = set()
        if os.path.exists(OUTPUT_FILE):
            logger.info(f"[INIT] Đang kiểm tra các số đã hoàn thành từ {OUTPUT_FILE}...")
            try:
                with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            phone = data.get("_phone_input")
                            if phone:
                                done.add(str(phone))
                logger.info(f"[INIT] Bỏ qua {len(done)} số điện thoại đã quét trước đó.")
            except Exception as e:
                logger.error(f"[ERROR] Lỗi đọc file kết quả cũ: {e}")
        return done

    def load_phones(self):
        if not os.path.exists(INPUT_FILE):
            logger.error(f"[ERROR] File data '{INPUT_FILE}' không tồn tại!")
            return

        logger.info(f"[INIT] Đang đọc file input: {INPUT_FILE}...")
        count = 0
        skipped = 0
        try:
            phones_to_load = []
            if INPUT_FILE.lower().endswith('.csv'):
                with open(INPUT_FILE, mode='r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        p = row.get('mobile', '').strip()
                        if p: phones_to_load.append(p)
            else:
                with open(INPUT_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        p = line.strip()
                        if p: phones_to_load.append(p)

            for p in phones_to_load:
                if p in self.done_phones:
                    skipped += 1
                    continue
                self.phone_queue.put(p)
                count += 1
                
            logger.info(f"[INIT] Đã nạp {count} số mới. Bỏ qua {skipped} số trùng.")
        except Exception as e:
            logger.error(f"[ERROR] Lỗi đọc file data: {e}")

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
                # Delay ngẫu nhiên để tránh bị trảm nhanh
                time.sleep(random.uniform(1.0, 3.0))
                
                proxies = None
                if acc_wrapper.proxy:
                    proxies = {"http": acc_wrapper.proxy, "https": acc_wrapper.proxy}
                
                result = acc_wrapper.client.getUserByPhone(phone, proxies=proxies)
                
                wait_seconds = 0
                error_code = 0
                
                if isinstance(result, dict):
                    error_code = result.get("error_code", 0)

                # --- XỬ LÝ LỖI ---
                if error_code != 0:
                    err_msg = result.get("error_message", "Unknown") if isinstance(result, dict) else str(result)
                    logger.warning(f"⚠️ [FAIL] {phone} (Code {error_code}): {err_msg} (Acc #{acc_wrapper.id})")

                    # Lỗi vượt hạn mức (221) hoặc lỗi hệ thống nặng
                    if error_code in [221, -366, -30]:
                        wait_seconds = LIMIT_COOLDOWN # Nghỉ 1 tiếng
                    
                    # Lỗi 312: Cần chờ đến thời điểm expireTs
                    elif error_code == 312:
                        expire_ts = result.get("data", {}).get("expireTs")
                        if expire_ts:
                            wait_seconds = (expire_ts / 1000) - time.time() + 60
                        if wait_seconds <= 0: wait_seconds = DEFAULT_COOLDOWN

                    # Đẩy lại số điện thoại vào hàng đợi vì chưa xử lý xong
                    self.phone_queue.put(phone)

                # --- XỬ LÝ THÀNH CÔNG ---
                else:
                    acc_wrapper.request_count += 1
                    data_save = result.get("data", {})
                    data_save["_phone_input"] = phone 
                    self.save_ndjson(data_save)
                    logger.info(f"✅ [OK] {phone} -> {data_save.get('display_name', 'Unknown')} (Acc #{acc_wrapper.id}: {acc_wrapper.request_count}/{LIMIT_REQUESTS})")

                    # Kiểm tra ngưỡng nghỉ định kỳ
                    if acc_wrapper.request_count >= LIMIT_REQUESTS:
                        logger.info(f"🛑 [MAX] Acc #{acc_wrapper.id} đạt {LIMIT_REQUESTS} req. Nghỉ {LIMIT_COOLDOWN//60} phút.")
                        wait_seconds = LIMIT_COOLDOWN
                        acc_wrapper.request_count = 0  

                self.manager.return_account(acc_wrapper, cooldown_seconds=wait_seconds)

            except Exception as e:
                logger.error(f"❌ [EXCEPTION] {e}")
                self.manager.return_account(acc_wrapper, cooldown_seconds=300) # Lỗi lạ cho nghỉ 5p
                self.phone_queue.put(phone) 

            finally:
                self.phone_queue.task_done()

    def run(self):
        total_acc = self.manager.active_queue.qsize()
        if total_acc == 0:
            logger.error("❌ Không có tài khoản nào sẵn sàng!")
            return

        num_workers = min(total_acc, 20)
        logger.info(f"🚀 Chạy {num_workers} luồng với {total_acc} tài khoản...")
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            for _ in range(num_workers):
                executor.submit(self.worker_task)
        
        self.phone_queue.join()
        logger.info("🏁 Đã xử lý xong toàn bộ danh sách.")

if __name__ == "__main__":
    crawler = ZaloCrawler()
    crawler.run()