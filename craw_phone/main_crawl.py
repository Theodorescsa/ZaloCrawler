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

# --- CẤU HÌNH ---
INPUT_FILE = r"phone.txt"
INPUT_ACCOUNTS = "accounts.json"
OUTPUT_FILE = "results.ndjson"
LOG_FILE = "crawler.log"

# KỊCH BẢN
LIMIT_HOURLY = 26          # 26 số mỗi giờ
LIMIT_COOLDOWN_HOUR = 3600 # Nghỉ 1 giờ (cho lỗi 312 hoặc khi đủ 26 số)

# CẤU HÌNH LOGGING
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

try:
    from zalo_client import ZaloClient
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from zalo_client import ZaloClient

class AccountWrapper:
    def __init__(self, acc_data, index):
        self.id = index
        self.proxy = acc_data.get('proxy')
        self.client = ZaloClient(
            secret_key_b64=acc_data['secret_key_b64'],
            cookie_string=acc_data['cookie']
        )
        self.cooldown_until = None
        self.hourly_count = 0

class AccountManager:
    def __init__(self, account_file):
        self.active_queue = Queue()
        self.cooldown_list = [] 
        self.lock = threading.Lock()
        self.load_accounts(account_file)

    def load_accounts(self, filepath):
        if not os.path.exists(filepath):
            logger.error(f"File {filepath} không tồn tại!")
            exit()
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for idx, acc in enumerate(data):
            self.active_queue.put(AccountWrapper(acc, idx))
        logger.info(f"Đã load {self.active_queue.qsize()} tài khoản.")

    def get_account(self):
        while True:
            try:
                return self.active_queue.get_nowait()
            except Empty:
                with self.lock:
                    now = datetime.now()
                    ready = [acc for acc in self.cooldown_list if now >= acc.cooldown_until]
                    for acc in ready:
                        self.cooldown_list.remove(acc)
                        logger.info(f"♻️ [RESTORE] Account #{acc.id} quay lại làm việc.")
                        self.active_queue.put(acc)
                time.sleep(2)

    def return_account(self, account, cooldown_seconds=0):
        if cooldown_seconds > 0:
            account.cooldown_until = datetime.now() + timedelta(seconds=cooldown_seconds)
            with self.lock:
                self.cooldown_list.append(account)
            resume_time = account.cooldown_until.strftime("%d/%m %H:%M:%S")
            logger.warning(f"🚫 [COOLDOWN] Acc #{account.id} nghỉ đến {resume_time} ({int(cooldown_seconds//60)} phút).")
        else:
            self.active_queue.put(account)

class ZaloCrawler:
    def __init__(self):
        self.manager = AccountManager(INPUT_ACCOUNTS)
        self.phone_queue = Queue()
        self.file_lock = threading.Lock()
        self.processed_phones = self._load_processed_phones()
        self._load_input_phones()

    def _load_processed_phones(self):
        processed = set()
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if "_phone_input" in data:
                            processed.add(str(data["_phone_input"]))
                    except: continue
        logger.info(f"Đã tìm thấy {len(processed)} số đã hoàn thành trước đó.")
        return processed

    def _load_input_phones(self):
        count = 0
        if not os.path.exists(INPUT_FILE): return
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                p = line.strip()
                if p and p not in self.processed_phones:
                    self.phone_queue.put(p)
                    count += 1
        logger.info(f"Đã nạp thêm {count} số mới vào hàng đợi.")

    def save_result(self, data):
        with self.file_lock:
            with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def worker_task(self):
        while True:
            try:
                phone = self.phone_queue.get(timeout=5)
            except Empty: break

            acc = self.manager.get_account()
            wait_sec = 0
            
            try:
                time.sleep(random.uniform(1.5, 3.0)) # Tránh quét quá nhanh
                proxies = {"http": acc.proxy, "https": acc.proxy} if acc.proxy else None
                result = acc.client.getUserByPhone(phone, proxies=proxies)
                
                err = result.get("error_code", 0) if isinstance(result, dict) else -999

                # --- XỬ LÝ LỖI ---
                if err != 0:
                    logger.warning(f"⚠️ [FAIL] {phone} | Code: {err} | Acc #{acc.id}")
                    
                    if err in [221, 313]: # LỖI QUÁ REQUEST -> NGHỈ ĐẾN MAI
                        now = datetime.now()
                        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=5)
                        wait_sec = (tomorrow - now).total_seconds()
                        logger.error(f"Critical 221: Acc #{acc.id} bị giới hạn ngày. Chờ đến sáng mai.")
                    
                    elif err == 312: # LỖI 312 -> NGHỈ 1 GIỜ
                        wait_sec = LIMIT_COOLDOWN_HOUR
                    
                    elif err in [-366, -30]: # LỖI HỆ THỐNG KHÁC
                        wait_sec = LIMIT_COOLDOWN_HOUR
                    
                    self.phone_queue.put(phone) # Đẩy lại số này để acc khác quét

                # --- XỬ LÝ THÀNH CÔNG ---
                else:
                    acc.hourly_count += 1
                    data = result.get("data", {})
                    data["_phone_input"] = phone
                    self.save_result(data)
                    logger.info(f"✅ [OK] {phone} -> {data.get('display_name')} (Acc #{acc.id}: {acc.hourly_count}/{LIMIT_HOURLY})")

                    if acc.hourly_count >= LIMIT_HOURLY:
                        logger.info(f"🏁 Acc #{acc.id} đã xong 26 số. Nghỉ 1 tiếng.")
                        wait_sec = LIMIT_COOLDOWN_HOUR
                        acc.hourly_count = 0 # Reset sau khi nghỉ xong

                self.manager.return_account(acc, wait_sec)

            except Exception as e:
                logger.error(f"Lỗi hệ thống: {e}")
                self.manager.return_account(acc, 300) # Lỗi ko xác định nghỉ 5p
                self.phone_queue.put(phone)
            finally:
                self.phone_queue.task_done()

    def run(self):
        num_threads = min(self.manager.active_queue.qsize(), 10)
        if num_threads == 0: return
        
        logger.info(f"🚀 Bắt đầu chạy với {num_threads} luồng.")
        with ThreadPoolExecutor(max_workers=num_threads) as exe:
            for _ in range(num_threads):
                exe.submit(self.worker_task)
        self.phone_queue.join()

if __name__ == "__main__":
    # Nếu bạn muốn delay 1 tiếng rồi mới chạy thật (như code cũ):
    logger.info("Chờ 1 tiếng theo yêu cầu...")
    time.sleep(3600)
    
    crawler = ZaloCrawler()
    crawler.run()