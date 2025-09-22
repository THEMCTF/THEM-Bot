import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()


class Database:
    _pool = None
    _instance = None
    conn: asyncpg.Connection = None
    DATA_DIR = Path(__file__).parent.parent / "data"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def init(cls):
        """Initialize the database connection and tables"""
        if not cls._is_postgres_installed():
            raise RuntimeError(
                "PostgreSQL is not installed. Please install:\n"
                "macOS: brew install postgresql\n"
                "Linux: sudo apt-get install postgresql\n"
                "Windows: https://www.postgresql.org/download/windows/"
            )

        # Ensure data directory exists
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize PostgreSQL data directory if needed
        if not (cls.DATA_DIR / "PG_VERSION").exists():
            cls._init_data_directory()

        if not cls._start_postgres_service():
            print("WARNING: Could not automatically start PostgreSQL service")

        print(f"PostgreSQL data directory: {cls.DATA_DIR}")

        # Get database credentials from environment variables
        db_user = os.getenv("DB_USER", "themcbot")
        db_password = os.getenv("DB_PASSWORD", "themcbot")
        db_name = os.getenv("DB_NAME", "themcbot")
        db_host = os.getenv("DB_HOST", "localhost")

        try:
            await cls._create_default_user()
            cls.conn = await asyncpg.connect(
                user=db_user,
                password=db_password,
                database=db_name,
                host=db_host,
            )
            await cls.create_dm_log_table()
            await cls.create_solutions_table()
            await cls.create_counters_table()
        except Exception as e:
            print(f"Connection error: {e}")
            print("\nTrying to create database and user...")
            await cls._setup_database()
            # Retry connection
            cls.conn = await asyncpg.connect(
                user=db_user,
                password=db_password,
                database=db_name,
                host=db_host,
            )
            await cls.create_dm_log_table()
            await cls.create_solutions_table()
            await cls.create_counters_table()

    @classmethod
    def _init_data_directory(cls):
        """Initialize a new PostgreSQL data directory"""
        try:
            subprocess.run(
                ["initdb", "-D", str(cls.DATA_DIR)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Failed to initialize data directory: {e.stderr}")
            raise

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
        """Start PostgreSQL service with custom data directory"""
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.run(
                    ["pg_ctl", "-D", str(Database.DATA_DIR), "start"], check=True
                )
            elif system == "Linux":
                subprocess.run(
                    ["pg_ctl", "-D", str(Database.DATA_DIR), "start"], check=True
                )
            elif system == "Windows":
                subprocess.run(
                    ["pg_ctl", "-D", str(Database.DATA_DIR), "start"], check=True
                )
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
            cls._pool = await asyncpg.create_pool(
                host="localhost",
                user="postgres",
                password="postgres",
                database="bot_db",
            )
        except Exception as e:
            print(f"Failed to create connection pool: {e}")
            raise

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
            
            CREATE TABLE IF NOT EXISTS changelog_subscribers (
                user_id BIGINT PRIMARY KEY
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
            return [
                {
                    "timestamp": row["timestamp"],
                    "username": row["username"],
                    "content": row["content"],
                    "has_attachments": row["has_attachments"],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Failed to get recent DMs: {e}")
            return []

    @classmethod
    async def add_solution(
        cls, channel_id: int, message_id: int, marked_by: int
    ) -> bool:
        """Add a solution to the database

        Args:
            channel_id: The ID of the channel where the solution was marked
            message_id: The ID of the message which has the solution
            marked_by: The ID of the user who marked it as a solution
        """
        query = """
            INSERT INTO solutions (channel_id, message_id, marked_by)
            VALUES ($1, $2, $3)
        """
        try:
            await cls.conn.execute(query, channel_id, message_id, marked_by)
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
            SELECT message_id, marked_by, timestamp
            FROM solutions
            WHERE channel_id = $1
            ORDER BY timestamp DESC
        """
        try:
            rows = await cls.conn.fetch(query, channel_id)
            return [
                {
                    "message_id": row["message_id"],
                    "marked_by": row["marked_by"],
                    "timestamp": row["timestamp"],
                }
                for row in rows
            ]
        except Exception as e:
            print(f"Failed to get solutions: {e}")
            return []

    @classmethod
    async def add_changelog_subscriber(cls, user_id: int) -> bool:
        """Add a user to the changelog subscribers list"""
        query = """
            INSERT INTO changelog_subscribers (user_id)
            VALUES ($1)
            ON CONFLICT DO NOTHING
        """
        try:
            await cls.conn.execute(query, user_id)
            return True
        except Exception as e:
            print(f"Failed to add subscriber: {e}")
            return False

    @classmethod
    async def remove_changelog_subscriber(cls, user_id: int) -> bool:
        """Remove a user from the changelog subscribers list"""
        query = "DELETE FROM changelog_subscribers WHERE user_id = $1"
        try:
            status = await cls.conn.execute(query, user_id)
            return status == "DELETE 1"
        except Exception as e:
            print(f"Failed to remove subscriber: {e}")
            return False

    @classmethod
    async def get_changelog_subscribers(cls) -> List[int]:
        """Get all changelog subscriber user IDs"""
        query = "SELECT user_id FROM changelog_subscribers"
        try:
            rows = await cls.conn.fetch(query)
            return [row["user_id"] for row in rows]
        except Exception as e:
            print(f"Failed to get subscribers: {e}")
            return []

    @classmethod
    async def update_changelog_history(cls, content: str) -> bool:
        """Add a new changelog entry to history"""
        query = "INSERT INTO changelog_history (content) VALUES ($1)"
        try:
            await cls.conn.execute(query, content)
            return True
        except Exception as e:
            print(f"Failed to update changelog history: {e}")
            return False

    @classmethod
    async def get_latest_changelog(cls) -> Optional[str]:
        """Get the most recent changelog entry"""
        query = """
            SELECT content
            FROM changelog_history
            ORDER BY updated_at DESC
            LIMIT 1
        """
        try:
            row = await cls.conn.fetchrow(query)
            return row["content"] if row else None
        except Exception as e:
            print(f"Failed to get latest changelog: {e}")
            return None

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
