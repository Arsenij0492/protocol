import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(os.path.join(LOG_DIR, "app.log"), 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def log_error(error_data):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = os.path.join(LOG_DIR, f"error_{timestamp}.json")
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(error_data, f, ensure_ascii=False, indent=2)
