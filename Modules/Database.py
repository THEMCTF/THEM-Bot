import asyncio
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()

class Database:
