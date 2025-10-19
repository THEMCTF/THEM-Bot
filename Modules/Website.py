import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import Any, List, Optional, Union

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("WEBSITE_SECRET_KEY")


class Website:
    async def get_otp_code():
        current_minute = int(time.time() // 60)
        hash_input = f"{SECRET_KEY}:{current_minute}".encode()
        hash_result = hashlib.sha256(hash_input).hexdigest()
        otp = int(hash_result[:8], 16) % 1000000
        print(f"{otp:06d}")
        return f"{otp:06d}"
