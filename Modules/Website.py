import hashlib
import os
import time

from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("WEBSITE_SECRET_KEY")


async def get_otp_code():
    now = time.time()
    current_minute = int(now // 60)
    h = hashlib.sha256(f"{SECRET_KEY}:{current_minute}".encode()).hexdigest()
    otp = int(h[:8], 16) % 1000000
    return f"{otp:06d}", 60 - (now % 60)
