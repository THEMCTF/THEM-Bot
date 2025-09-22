import os
from typing import List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()


class Database:
    _pool = None
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def init(cls):
        """Initialize the database connection and tables"""
        try:
            cls.conn = await asyncpg.connect(
                host="localhost",
                user="postgres",
                password="postgres",
                database="bot_db",
            )
            await cls.create_dm_log_table()
        except Exception as e:
            print(f"Database initialization failed: {e}")
            raise

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
        """
        try:
            await cls.conn.execute(query)
        except Exception as e:
            print(f"Failed to create dm_logs table: {e}")
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
