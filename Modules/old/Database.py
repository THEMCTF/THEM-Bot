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
    _pool = None
    _instance = None
    conn: asyncpg.Connection = None
    DATA_DIR = (
        Path(__file__).parent.parent / "data"
    )  # For bot data only, not PostgreSQL

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_latest_dm_timestamp(cls) -> Optional[datetime]:
        """Get timestamp of the most recent DM in the database"""
        if not cls.conn:
            print("Database not initialized")
            return None

        query = """
            SELECT timestamp
            FROM dm_logs
            ORDER BY timestamp DESC
            LIMIT 1
            """
        try:
            timestamp = await cls.conn.fetchval(query)
            return timestamp if timestamp else datetime.min.replace(tzinfo=timezone.utc)
        except Exception as e:
            print(f"Failed to get latest DM timestamp: {e}")
            return datetime.min.replace(tzinfo=timezone.utc)

    @classmethod
    async def init(cls) -> bool:
        """Initialize the database connection and tables"""
        if not cls._is_postgres_installed():
            raise RuntimeError(
                "PostgreSQL is not installed. Please install:\n"
                "macOS: brew install postgresql\n"
                "Linux: sudo apt-get install postgresql\n"
                "Windows: https://www.postgresql.org/download/windows/"
            )

        # Ensure data directory exists for bot data
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not cls._start_postgres_service():
            print("WARNING: Could not automatically start PostgreSQL service")

        # Get database credentials from environment variables
        db_user = os.getenv("DB_USER", "themcbot")
        db_password = os.getenv("DB_PASSWORD", "themcbot")
        db_name = os.getenv("DB_NAME", "themcbot")
        db_host = os.getenv("DB_HOST", "localhost")
        max_tries = 3

        tries = 0
        max_tries = 3
        while tries < max_tries:
            try:
                await cls._create_default_user()
                cls.conn = await asyncpg.connect(
                    user=db_user,
                    password=db_password,
                    database=db_name,
                    host=db_host,
                )
                # Create all required tables
                await cls._create_tables()
                print(
                    "\033[32mDatabase connection and tables initialized successfully\033[0m"
                )
                return True
            except Exception as e:
                tries += 1
                if tries == max_tries:
                    print(
                        f"\033[31mFailed to initialize database after {max_tries} attempts: {e}\033[0m"
                    )
                    return False
                print(f"\nDatabase connection attempt {tries} failed: {e}")
                print("Trying to create database and user...")
                try:
                    await cls._setup_database()
                except Exception as setup_error:
                    print(f"Failed to setup database: {setup_error}")
                await asyncio.sleep(1)  # Wait a bit before retrying

        return False

    @classmethod
    async def _create_tables(cls):
        """Create all required tables"""
        if not cls.conn:
            raise Exception("Database connection not initialized")

        await cls.create_dm_log_table()
        await cls.create_solutions_table()
        await cls.create_counters_table()
        await cls.create_ctfs_table()
        await cls.create_active_ctf_buttons_table()
        await cls.create_pending_announcements_table()

    @staticmethod
    def _is_postgres_installed():
        """Check if PostgreSQL is installed."""
        if platform.system() == "Darwin":  # macOS
            return shutil.which("postgres") is not None
        elif platform.system() == "Linux":
            return shutil.which("postgresql") is not None
        elif platform.system() == "Windows":
            return shutil.which("pg_ctl") is not None
        return False

    @staticmethod
    def _start_postgres_service():
        """Start PostgreSQL service using system defaults"""
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.run(["brew", "services", "start", "postgresql"], check=True)
            elif system == "Linux":
                subprocess.run(["sudo", "service", "postgresql", "start"], check=True)
            elif system == "Windows":
                subprocess.run(["net", "start", "postgresql"], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    async def _create_default_user():
        """Create default database user if it doesn't exist"""
        try:
            # Try with postgres user first
            system_conn = await asyncpg.connect(
                user="postgres", database="postgres", host="localhost"
            )
        except asyncpg.InvalidAuthorizationSpecificationError:
            # On macOS, try with current system user
            system_conn = await asyncpg.connect(database="postgres", host="localhost")

        try:
            await system_conn.execute(
                """
                DO $$ 
                BEGIN
                    CREATE USER themcbot WITH PASSWORD 'themcbot';
                EXCEPTION WHEN DUPLICATE_OBJECT THEN
                    NULL;
                END $$;
            """
            )
            # Grant necessary permissions
            await system_conn.execute(
                """
                DO $$ 
                BEGIN
                    ALTER USER themcbot CREATEDB;
                EXCEPTION WHEN DUPLICATE_OBJECT THEN
                    NULL;
                END $$;
            """
            )
        finally:
            await system_conn.close()

    @staticmethod
    async def _setup_database():
        """Create database and grant permissions"""
        try:
            # Try with postgres user first
            system_conn = await asyncpg.connect(
                user="postgres", database="postgres", host="localhost"
            )
        except asyncpg.InvalidAuthorizationSpecificationError:
            # On macOS, try with current system user
            system_conn = await asyncpg.connect(database="postgres", host="localhost")

        try:
            # Check if database exists
            exists = await system_conn.fetchval(
                """
                SELECT 1 FROM pg_database WHERE datname = 'themcbot'
            """
            )

            if not exists:
                await system_conn.execute("CREATE DATABASE themcbot")

            await system_conn.execute(
                """
                GRANT ALL PRIVILEGES ON DATABASE themcbot TO themcbot;
            """
            )
        finally:
            await system_conn.close()

    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            await cls.create_pool()
        return cls._pool

    @classmethod
    async def create_pool(cls):
        """Create the connection pool"""
        try:
            db_user = os.getenv("DB_USER", "themcbot")
            db_password = os.getenv("DB_PASSWORD", "themcbot")
            db_name = os.getenv("DB_NAME", "themcbot")
            db_host = os.getenv("DB_HOST", "localhost")

            cls._pool = await asyncpg.create_pool(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
            )
        except Exception as e:
            print(f"Failed to create connection pool: {e}")
            raise

    @classmethod
    async def create_ctfs_table(cls):
        """Create the ctf_events table if it doesn't exist"""
        query = """
            CREATE TABLE IF NOT EXISTS ctf_events (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                start_time TIMESTAMPTZ NOT NULL,
                end_time TIMESTAMPTZ NOT NULL,
                website TEXT,
                team_name TEXT,
                password TEXT,
                discord_invite TEXT,
                sheet_url TEXT,
                categories TEXT[],
                registered_by BIGINT,
                registered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """
        await cls.conn.execute(query)

    @classmethod
    async def create_active_ctf_buttons_table(cls):
        """Create the active_ctf_buttons table if it doesn't exist."""
        query = """
            CREATE TABLE IF NOT EXISTS active_ctf_buttons (
                ctf_name TEXT PRIMARY KEY,
                message_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                end_time TIMESTAMPTZ NOT NULL
            );
        """
        await cls.conn.execute(query)

    @classmethod
    async def create_pending_announcements_table(cls):
        """Create the pending_announcements table if it doesn't exist."""
        query = """
            CREATE TABLE IF NOT EXISTS pending_announcements (
                ctf_name_input TEXT PRIMARY KEY,
                ctf_name TEXT NOT NULL,
                end_time TIMESTAMPTZ NOT NULL
            );
        """
        await cls.conn.execute(query)

    @classmethod
    async def create_dm_log_table(cls):
        """Create the DM logs table if it doesn't exist"""
        query = """
            CREATE TABLE IF NOT EXISTS dm_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                message_id BIGINT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                has_attachments BOOLEAN DEFAULT FALSE,
                attachment_count INTEGER DEFAULT 0
            );
        """
        try:
            await cls.conn.execute(query)
        except Exception as e:
            print(f"Failed to create dm_logs table: {e}")
            raise

    @classmethod
    async def create_counters_table(cls):
        """Create the counters table if it doesn't exist"""
        query = """
            CREATE TABLE IF NOT EXISTS counters (
                name TEXT PRIMARY KEY,
                value BIGINT DEFAULT 0
            );
            INSERT INTO counters (name, value) 
            VALUES ('them_counter', 0)
            ON CONFLICT (name) DO NOTHING;
        """
        try:
            await cls.conn.execute(query)
        except Exception as e:
            print(f"Failed to create counters table: {e}")
            raise

    @classmethod
    async def create_solutions_table(cls):
        """Create the solutions table if it doesn't exist"""
        query = """
            CREATE TABLE IF NOT EXISTS solutions (
                id SERIAL PRIMARY KEY,
                channel_id BIGINT NOT NULL,
                message_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                marked_by BIGINT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """
        try:
            await cls.conn.execute(query)
        except Exception as e:
            print(f"Failed to create solutions table: {e}")
            raise

    @classmethod
    async def log_dm(
        cls,
        user_id: int,
        username: str,
        content: str,
        message_id: int,
        has_attachments: bool = False,
        attachment_count: int = 0,
    ) -> bool:
        """Log a DM message in the database

        Args:
            user_id: The user's Discord ID
            username: The user's Discord username
            content: The message content
            message_id: The Discord message ID
            has_attachments: Whether the message has attachments
            attachment_count: Number of attachments
        """
        query = """
            INSERT INTO dm_logs 
            (user_id, username, content, message_id, has_attachments, attachment_count)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        try:
            await cls.conn.execute(
                query,
                user_id,
                username,
                content,
                message_id,
                has_attachments,
                attachment_count,
            )
            return True
        except Exception as e:
            print(f"Failed to log DM: {e}")
            return False

    @classmethod
    async def log_ctf(
        cls,
        name: str,
        start_time: datetime,
        end_time: datetime,
        website: str,
        team_name: str,
        password: str,
        discord_invite: str,
        sheet_url: str,
        categories: list,
        registered_by: int,
    ) -> bool:
        """Log a new CTF event in the database."""
        query = """
            INSERT INTO ctf_events
            (name, start_time, end_time, website, team_name, password, discord_invite, sheet_url, categories, registered_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        try:
            await cls.conn.execute(
                query,
                name,
                start_time,
                end_time,
                website,
                team_name,
                password,
                discord_invite,
                sheet_url,
                categories,
                registered_by,
            )
            print(f"Successfully logged CTF: {name}")
            return True
        except Exception as e:
            print(f"Failed to log CTF event: {e}")
            return False

    @classmethod
    async def add_active_button(
        cls, ctf_name: str, message_id: int, channel_id: int, end_time: datetime
    ):
        """Add an active CTF button to the database."""
        query = """
            INSERT INTO active_ctf_buttons (ctf_name, message_id, channel_id, end_time)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (ctf_name) DO UPDATE SET
                message_id = EXCLUDED.message_id,
                channel_id = EXCLUDED.channel_id,
                end_time = EXCLUDED.end_time;
        """
        try:
            await cls.conn.execute(query, ctf_name, message_id, channel_id, end_time)
            return True
        except Exception as e:
            print(f"Failed to add active button: {e}")
            return False

    @classmethod
    async def get_active_buttons(cls) -> List[dict]:
        """Get all active CTF buttons from the database."""
        query = (
            "SELECT ctf_name, message_id, channel_id, end_time FROM active_ctf_buttons"
        )
        try:
            rows = await cls.conn.fetch(query)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to get active buttons: {e}")
            return []

    @classmethod
    async def remove_active_button(cls, ctf_name: str) -> bool:
        """Remove an active CTF button from the database."""
        query = "DELETE FROM active_ctf_buttons WHERE ctf_name = $1"
        try:
            await cls.conn.execute(query, ctf_name)
            return True
        except Exception as e:
            print(f"Failed to remove active button: {e}")
            return False

    @classmethod
    async def add_pending_announcement(
        cls, ctf_name_input: str, ctf_name: str, end_time: datetime
    ):
        """Add a pending announcement to the database."""
        query = """
            INSERT INTO pending_announcements (ctf_name_input, ctf_name, end_time)
            VALUES ($1, $2, $3)
            ON CONFLICT (ctf_name_input) DO UPDATE SET
                ctf_name = EXCLUDED.ctf_name,
                end_time = EXCLUDED.end_time;
        """
        try:
            await cls.conn.execute(query, ctf_name_input, ctf_name, end_time)
            return True
        except Exception as e:
            print(f"Failed to add pending announcement: {e}")
            return False

    @classmethod
    async def get_pending_announcements(cls) -> List[dict]:
        """Get all pending announcements from the database."""
        query = "SELECT ctf_name_input, ctf_name, end_time FROM pending_announcements"
        try:
            rows = await cls.conn.fetch(query)
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Failed to get pending announcements: {e}")
            return []

    @classmethod
    async def remove_pending_announcement(cls, ctf_name_input: str) -> bool:
        """Remove a pending announcement from the database."""
        query = "DELETE FROM pending_announcements WHERE ctf_name_input = $1"
        await cls.conn.execute(query, ctf_name_input)

    @classmethod
    async def get_recent_dms(cls, limit: int = 10) -> List[dict]:
        """Get recent DM logs from the database

        Args:
            limit (int): Maximum number of logs to retrieve

        Returns:
            List[dict]: List of DM log entries with timestamp, username, content, etc.
        """
        query = """
            SELECT 
                timestamp,
                username,
                content,
                has_attachments
            FROM dm_logs
            ORDER BY timestamp DESC
            LIMIT $1
        """
        try:
            rows = await cls.conn.fetch(query, limit)
            result = [
                {
                    "timestamp": row["timestamp"],
                    "username": row["username"],
                    "content": row["content"],
                    "has_attachments": row["has_attachments"],
                }
                for row in rows
            ]
        except Exception as e:
            from Modules import log  # Import here to avoid circular dependency

            # Log the error using the logger
            log.log(text=f"Failed to get recent DMs: {e}", color=0xFF0000, type="ERROR")
            print(f"Failed to get recent DMs: {e}")
            return []

    @classmethod
    async def add_solution(
        cls, channel_id: int, message_id: int, user_id: int, marked_by: int
    ) -> bool:
        """Add a solution to the database

        Args:
            channel_id: The ID of the channel where the solution was marked
            message_id: The ID of the message which has the solution
            user_id: The ID of the user who provided the solution
            marked_by: The ID of the user who marked it as a solution
        """
        query = """
            INSERT INTO solutions (channel_id, message_id, user_id, marked_by)
            VALUES ($1, $2, $3, $4)
        """
        try:
            await cls.conn.execute(query, channel_id, message_id, user_id, marked_by)
            print(
                f"Solution added: channel_id={channel_id}, message_id={message_id}, user_id={user_id}, marked_by={marked_by}"
            )
            return True
        except Exception as e:
            print(f"Failed to add solution: {e}")
            return False

    @classmethod
    async def get_solutions(cls, channel_id: int) -> List[dict]:
        """Get solutions for a specific channel

        Args:
            channel_id: The ID of the channel to get solutions for

        Returns:
            List[dict]: List of solutions with message_id and marked_by information
        """
        query = """
            SELECT channel_id, message_id, user_id, marked_by, timestamp
            FROM solutions
            WHERE channel_id = $1
            ORDER BY timestamp DESC
        """
        try:
            rows = await cls.conn.fetch(query, channel_id)
            return [
                {
                    "channel_id": row["channel_id"],
                    "message_id": row["message_id"],
                    "user_id": row["user_id"],
                    "marked_by": row["marked_by"],
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Failed to get solutions: {e}")
            return []

    @classmethod
    async def increment_them_counter(cls) -> bool:
        """Increment the 'them' counter by 1"""
        query = """
            UPDATE counters 
            SET value = value + 1 
            WHERE name = 'them_counter'
            RETURNING value
        """
        try:
            result = await cls.conn.fetchval(query)
            return bool(result)
        except Exception as e:
            print(f"Failed to increment them counter: {e}")
            return False

    @classmethod
    async def get_them_counter(cls) -> int:
        """Get the current value of the 'them' counter"""
        query = "SELECT value FROM counters WHERE name = 'them_counter'"
        try:
            value = await cls.conn.fetchval(query)
            return value or 0
        except Exception as e:
            print(f"Failed to get them counter: {e}")
            return 0

    async def get_them_counter(cls) -> int:
        """Get the current value of the 'them' counter"""
        query = "SELECT value FROM counters WHERE name = 'them_counter'"
        try:
            value = await cls.conn.fetchval(query)
            return value or 0
        except Exception as e:
            print(f"Failed to get them counter: {e}")
            return 0
