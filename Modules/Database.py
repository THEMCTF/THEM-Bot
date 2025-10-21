import asyncio
import os
from pathlib import Path
from typing import Any, List, Optional, Union

import asyncpg
from dotenv import load_dotenv

load_dotenv()


class Database:
    DATA_DIR = Path(__file__).parent.parent / "data"

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Establish connection pool to PostgreSQL database."""
        if self.pool is not None:
            return  # Already connected

        self.pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            min_size=1,
            max_size=10,
        )

    async def close(self):
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def create_table(
        self,
        table_name: str,
        columns: List[tuple],
        if_not_exists: bool = True
    ):
        """
        Create a new table with specified columns.

        Args:
            table_name: Name of the table to create
            columns: List of tuples (column_name, data_type)
                     Example: [("name", "TEXT"), ("age", "INTEGER")]
            if_not_exists: If True, don't error if table already exists

        Example:
            await db.create_table("users", [
                ("name", "TEXT"),
                ("email", "TEXT"),
                ("age", "INTEGER")
            ])
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        if not columns:
            raise ValueError("Must provide at least one column")

        async with self.pool.acquire() as conn:
            if_not_exists_clause = "IF NOT EXISTS" if if_not_exists else ""

            # Build column definitions
            col_defs = [f'"{col_name}" {data_type}' for col_name, data_type in columns]
            col_defs_str = ", ".join(col_defs)

            query = f"""
                CREATE TABLE {if_not_exists_clause} "{table_name}" (
                    id SERIAL PRIMARY KEY,
                    {col_defs_str}
                );
            """

            await conn.execute(query)
            print(f"✓ Table '{table_name}' created successfully")

    async def drop_table(self, table_name: str, if_exists: bool = True):
        """
        Drop a table from the database.

        Args:
            table_name: Name of the table to drop
            if_exists: If True, don't error if table doesn't exist
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            if_exists_clause = "IF EXISTS" if if_exists else ""
            query = f'DROP TABLE {if_exists_clause} "{table_name}"'
            await conn.execute(query)
            print(f"✓ Table '{table_name}' dropped successfully")

    async def find_rows(
        self,
        table_name: str,
        column_name: str,
        value: Any,
    ) -> List[asyncpg.Record]:
        """
        Find all row IDs where a column matches a specific value.

        Args:
            table_name: Name of the table to search
            column_name: Name of the column to search in
            value: Value to search for

        Returns:
            List of matching row records (dictionaries).

        Example:
            rows = await db.find_rows("solutions", "channel_id", 123456789)
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            if not await self._table_exists(conn, table_name):
                # If the table doesn't exist, there are no rows to find.
                return []

            query = (
                f'SELECT * FROM "{table_name}" WHERE "{column_name}" = $1 ORDER BY id'
            )
            rows = await conn.fetch(query, value)
            return rows

    async def delete_rows(
        self,
        table_name: str,
        row_ids: Union[int, List[int]],
        compact: bool = False,
    ):
        """
        Delete specific rows from a table.

        Args:
            table_name: Name of the table
            row_ids: Single row ID or list of row IDs to delete
            compact: If True, renumber remaining rows to fill gaps

        Example:
            await db.delete_rows("solutions", [1, 3, 5], compact=True)
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        if isinstance(row_ids, int):
            row_ids = [row_ids]

        if not row_ids:
            return

        async with self.pool.acquire() as conn:
            if not await self._table_exists(conn, table_name):
                await self.create_table(table_name)
                print(f"Table '{table_name}' did not exist and was created.")

            async with conn.transaction():
                # Delete the specified rows
                query = f'DELETE FROM "{table_name}" WHERE id = ANY($1)'
                await conn.execute(query, row_ids)
                print(f"✓ Deleted {len(row_ids)} row(s) from '{table_name}'")

                # Compact if requested
                if compact:
                    await self._compact_table(conn, table_name)

    async def delete_where(
        self,
        table_name: str,
        column_name: str,
        value: Any,
        compact: bool = False,
    ):
        """
        Delete all rows where a column matches a value.

        Args:
            table_name: Name of the table
            column_name: Column to check
            value: Value to match
            compact: If True, renumber remaining rows to fill gaps

        Example:
            # Delete all solutions by user 123456789
            await db.delete_where("solutions", "user_id", 123456789, compact=True)
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            if not await self._table_exists(conn, table_name):
                await self.create_table(table_name)
                print(f"Table '{table_name}' did not exist and was created.")

            async with conn.transaction():
                # Delete matching rows
                query = f'DELETE FROM "{table_name}" WHERE "{column_name}" = $1'
                result = await conn.execute(query, value)

                # Extract number of deleted rows from result string like "DELETE 3"
                deleted_count = int(result.split()[-1]) if result.split() else 0
                print(
                    f"✓ Deleted {deleted_count} row(s) from '{table_name}' where {column_name} = {value}"
                )

                # Compact if requested
                if compact:
                    await self._compact_table(conn, table_name)

    async def _compact_table(self, conn: asyncpg.Connection, table_name: str):
        """
        Renumber row IDs to remove gaps (1, 2, 3, 4, ...).
        This is called internally after deletions when compact=True.
        """
        # Get all remaining rows in order
        rows = await conn.fetch(f'SELECT * FROM "{table_name}" ORDER BY id')

        if not rows:
            # Reset sequence to 1 if table is empty
            await conn.execute(f'ALTER SEQUENCE "{table_name}_id_seq" RESTART WITH 1')
            print(f"✓ Table '{table_name}' is now empty, sequence reset")
            return

        # Get column names (excluding id)
        column_names = await self._get_column_names(conn, table_name)

        # Delete all rows
        await conn.execute(f'DELETE FROM "{table_name}"')

        # Reset the sequence
        await conn.execute(f'ALTER SEQUENCE "{table_name}_id_seq" RESTART WITH 1')

        # Re-insert rows with new sequential IDs
        if column_names:
            col_list = ", ".join([f'"{col}"' for col in column_names])
            placeholders = ", ".join([f"${i+1}" for i in range(len(column_names))])
            query = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'

            for row in rows:
                values = [row[col] for col in column_names]
                await conn.execute(query, *values)

        print(f"✓ Compacted '{table_name}': renumbered {len(rows)} row(s)")

    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            tables = await conn.fetch(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """
            )
            return [t["table_name"] for t in tables]

    async def _table_exists(self, conn: asyncpg.Connection, table_name: str) -> bool:
        """Check if a table exists in the database."""
        result = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = $1
            );
            """,
            table_name,
        )
        return result

    async def _get_column_names(
        self,
        conn: asyncpg.Connection,
        table_name: str
    ) -> List[str]:
        """Fetch column names for a table, excluding 'id'."""
        columns = await conn.fetch(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = $1
            AND column_name != 'id'
            ORDER BY ordinal_position;
            """,
            table_name,
        )
        return [c["column_name"] for c in columns]

    async def _get_next_row_id(self, conn: asyncpg.Connection, table_name: str) -> int:
        """Get the next available row ID (max id + 1, or 1 if table is empty)."""
        result = await conn.fetchval(
            f'SELECT COALESCE(MAX(id), 0) + 1 FROM "{table_name}"'
        )
        return result

    async def _ensure_row_exists(
        self,
        conn: asyncpg.Connection,
        table_name: str,
        row_id: int
    ):
        """Check if a row exists, create it if it doesn't."""
        result = await conn.fetchval(
            f'SELECT EXISTS(SELECT 1 FROM "{table_name}" WHERE id = $1)', row_id
        )
        if not result:
            # Insert a new row with the given id
            await conn.execute(
                f'INSERT INTO "{table_name}" (id) VALUES ($1) ON CONFLICT (id) DO NOTHING',
                row_id,
            )

    async def add_to_table(
        self,
        table_name: str,
        data: Union[Any, List[Any], List[List[Any]]],
        start_row: Union[int, str, None] = None,
        start_col: Union[int, str] = 1,
        direction: str = "row",
    ):
        """
        Adds data to a table, starting at a specific cell.
        Creates rows if they don't exist.

        Args:
            table_name: The name of the table to modify
            data: Single value, 1D list, or 2D list (grid)
            start_row: Starting row ID, "next" for auto-increment, or None (defaults to "next")
            start_col: Starting column index (1-based, excluding 'id'), or "next" (not implemented)
            direction: 'row' or 'column' for 1D lists

        Raises:
            ValueError: If start_col is out of bounds or direction is invalid
            RuntimeError: If database is not connected
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        if direction not in ("row", "column"):
            raise ValueError("direction must be 'row' or 'column'")

        async with self.pool.acquire() as conn:
            # Check if table exists
            if not await self._table_exists(conn, table_name):
                await self.create_table(table_name)
                print(f"Table '{table_name}' did not exist and was created.")

            column_names = await self._get_column_names(conn, table_name)

            if not column_names:
                raise ValueError(
                    f"Table '{table_name}' has no columns (excluding 'id')"
                )

            # Handle "next" for start_row
            if str(start_row).lower() == "next":
                start_row = await self._get_next_row_id(conn, table_name)

            # Handle "next" for start_col (not common, but supported)
            if str(start_col).lower() == "next":
                start_col = 1  # Default to first column for "next"

            if start_col < 1 or start_col > len(column_names):
                raise ValueError(
                    f"start_col ({start_col}) is out of bounds. "
                    f"Table has {len(column_names)} columns (excluding 'id')."
                )

            async with conn.transaction():
                # Single value
                if not isinstance(data, list):
                    await self._ensure_row_exists(conn, table_name, start_row)
                    col_name = column_names[start_col - 1]
                    query = f'UPDATE "{table_name}" SET "{col_name}" = $1 WHERE id = $2'
                    await conn.execute(query, data, start_row)
                    print(f"✓ Updated {table_name}[{start_row}, {start_col}] = {data}")

                # 2D list (grid)
                elif data and isinstance(data[0], list):
                    for r_offset, row_data in enumerate(data):
                        current_row_id = start_row + r_offset
                        await self._ensure_row_exists(conn, table_name, current_row_id)

                        set_clauses = []
                        args = []
                        for c_offset, cell_data in enumerate(row_data):
                            current_col_index = start_col - 1 + c_offset
                            if current_col_index < len(column_names):
                                col_name = column_names[current_col_index]
                                set_clauses.append(f'"{col_name}" = ${len(args) + 1}')
                                args.append(cell_data)

                        if set_clauses:
                            args.append(current_row_id)
                            query = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE id = ${len(args)}'
                            await conn.execute(query, *args)

                    print(
                        f"✓ Updated {table_name} grid: {len(data)} rows × {len(data[0])} cols starting at [{start_row}, {start_col}]"
                    )

                # 1D list
                else:
                    if direction == "row":
                        await self._ensure_row_exists(conn, table_name, start_row)
                        set_clauses = []
                        args = []

                        for i, value in enumerate(data):
                            current_col_index = start_col - 1 + i
                            if current_col_index < len(column_names):
                                col_name = column_names[current_col_index]
                                set_clauses.append(f'"{col_name}" = ${len(args) + 1}')
                                args.append(value)

                        if set_clauses:
                            args.append(start_row)
                            query = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE id = ${len(args)}'
                            await conn.execute(query, *args)
                            print(
                                f"✓ Updated {table_name} row {start_row}: {len(data)} values"
                            )

                    else:  # direction == "column"
                        col_name = column_names[start_col - 1]
                        for i, value in enumerate(data):
                            current_row_id = start_row + i
                            await self._ensure_row_exists(
                                conn, table_name, current_row_id
                            )
                            query = f'UPDATE "{table_name}" SET "{col_name}" = $1 WHERE id = $2'
                            await conn.execute(query, value, current_row_id)

                        print(
                            f"✓ Updated {table_name} column {start_col}: {len(data)} values"
                        )

    async def read_table(
        self,
        table_name: str,
        start_row: int = None,
        start_col: int = None,
        num_rows: int = None,
        num_cols: int = None,
    ) -> Union[Any, List[Any], List[List[Any]]]:
        """
        Read data from a table starting at specific coordinates.

        Args:
            table_name: The name of the table to read from
            start_row: Starting row ID
            start_col: Starting column index (1-based, excluding 'id')
            num_rows: Number of rows to read
            num_cols: Number of columns to read

        Returns:
            Single value if num_rows=1 and num_cols=1
            1D list if either num_rows=1 or num_cols=1
            2D list otherwise

        Raises:
            ValueError: If coordinates are out of bounds
            RuntimeError: If database is not connected
        """
        if self.pool is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self.pool.acquire() as conn:
            # Check if table exists
            if not await self._table_exists(conn, table_name):
                await self.create_table(table_name)
                print(f"Table '{table_name}' did not exist and was created.")

            if start_row is None and start_col is None and num_rows is None and num_cols is None:
                query = f'SELECT * FROM "{table_name}" ORDER BY id'
                rows = await conn.fetch(query)
                return rows

            column_names = await self._get_column_names(conn, table_name)

            if not column_names:
                raise ValueError(
                    f"Table '{table_name}' has no columns (excluding 'id')"
                )

            if start_col < 1 or start_col > len(column_names):
                raise ValueError(
                    f"start_col ({start_col}) is out of bounds. "
                    f"Table has {len(column_names)} columns (excluding 'id')."
                )

            end_col = min(start_col + num_cols - 1, len(column_names))
            cols_to_read = column_names[start_col - 1 : end_col]

            if not cols_to_read:
                raise ValueError("No columns to read")

            # Build query
            col_list = ", ".join([f'"{col}"' for col in cols_to_read])
            query = f'SELECT {col_list} FROM "{table_name}" WHERE id >= $1 AND id < $2 ORDER BY id'

            rows = await conn.fetch(query, start_row, start_row + num_rows)

            # Format result based on dimensions
            if num_rows == 1 and num_cols == 1:
                # Single value
                return rows[0][cols_to_read[0]] if rows else None
            elif num_rows == 1:
                # Single row
                return (
                    [rows[0][col] for col in cols_to_read]
                    if rows
                    else [None] * len(cols_to_read)
                )
            elif num_cols == 1:
                # Single column
                return [row[cols_to_read[0]] for row in rows]
            else:
                # 2D grid
                return [[row[col] for col in cols_to_read] for row in rows]

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()


# Example usage
async def main():
    async with Database() as db:
        # List existing tables
        tables = await db.list_tables()
        print(f"Existing tables: {tables}")

        # Create a new table
        await db.create_table(
            "users",
            [
                ("first_name", "TEXT"),
                ("last_name", "TEXT"),
                ("age", "INTEGER"),
                ("email", "TEXT"),
            ],
        )

        # Add row - automatically uses next available row ID
        await db.add_to_table("users", ["John", "Doe", 30, "john@example.com"])

        # Add another row - also uses next ID (will be row 2)
        await db.add_to_table(
            "users", ["Alice", "Smith", 28, "alice@example.com"], start_row="next"
        )

        # Add to specific row
        await db.add_to_table(
            "users", ["Bob", "Jones", 32, "bob@example.com"], start_row=5
        )

        # Add column of ages starting at row 1
        await db.add_to_table(
            "users", [25, 30, 35], start_row=1, start_col=3, direction="column"
        )

        # Add 2D grid starting at next available row
        await db.add_to_table(
            "users",
            [
                ["Emma", "Wilson", 27, "emma@example.com"],
                ["Mike", "Brown", 31, "mike@example.com"],
            ],
            start_row="next",
        )

        # Read single value
        value = await db.read_table("users", start_row=1, start_col=1)
        print(f"Single value: {value}")

        # Read entire row
        row = await db.read_table("users", start_row=1, num_cols=4)
        print(f"Row: {row}")

        # Read column
        col = await db.read_table("users", start_row=1, start_col=1, num_rows=3)
        print(f"Column: {col}")

        # Read grid
        grid = await db.read_table(
            "users", start_row=1, start_col=1, num_rows=2, num_cols=3
        )
        print(f"Grid: {grid}")

        # --- NEW: Search and Delete Examples ---

        # Find all rows where first_name is "John"
        john_rows = await db.find_rows("users", "first_name", "John")
        print(f"Rows with John: {john_rows}")

        # Delete specific rows by ID
        await db.delete_rows("users", [2, 4], compact=False)

        # Delete all rows where age is 30, and compact the table
        await db.delete_where("users", "age", 30, compact=True)

        print("\n=== Discord Bot Example ===")
        # For your Discord bot - delete all solutions by a user:
        # user_id = message.author.id
        # await db.delete_where("solutions", "user_id", user_id, compact=True)
        print("See commented code above for Discord bot usage")

        # Clean up (optional)
        # await db.drop_table("users")


if __name__ == "__main__":
    asyncio.run(main())