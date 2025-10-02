import asyncio
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import asyncpg
from dotenv import load_dotenv

load_dotenv()


class Database:
    DATA_DIR = (
        Path(__file__).parent.parent / "data"
    )  # For bot data only, not PostgreSQL

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )

    async def close(self):
        await self.pool.close()

    # add to a table, specify row/collum, if it's a list then go in the directon of the row/colum
    # or if a cell is just given, then there's probaly only one value, so just add it there)
    async def add_to_table(
        self,
        table_name: str,
        data,
        start_row: int,
        start_col: int,
        direction: str = "row",
    ):
        """
        Adds data to a table, starting at a specific cell.
        This function assumes the table has a primary key column named 'id'
        to identify rows for updates.

        Args:
            table_name (str): The name of the table to modify.
            data: The data to add. Can be a single value, a list (for a row/column),
                  or a list of lists (for a grid).
            start_row (int): The starting row identifier (e.g., primary key 'id').
            start_col (int): The starting column index (1-based).
            direction (str): 'row' or 'column'. Only used if data is a 1D list.
        """
        async with self.pool.acquire() as conn:
            # Fetch column names for the table to build dynamic queries
            # We exclude the 'id' column from our list of updatable columns.
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
            column_names = [c["column_name"] for c in columns]

            if start_col < 1 or start_col > len(column_names):
                raise ValueError(f"start_col is out of bounds for table {table_name}")

            async with conn.transaction():
                if not isinstance(data, list):  # Single value
                    col_name = column_names[start_col - 1]
                    query = f'UPDATE "{table_name}" SET "{col_name}" = $1 WHERE id = $2'
                    await conn.execute(query, data, start_row)
                    print(
                        f"Updated single value in {table_name} at ({start_row}, {start_col})"
                    )

                elif isinstance(data[0], list):  # 2D list (grid)
                    for r_offset, row_data in enumerate(data):
                        current_row_id = start_row + r_offset
                        for c_offset, cell_data in enumerate(row_data):
                            current_col_index = start_col - 1 + c_offset
                            if current_col_index < len(column_names):
                                col_name = column_names[current_col_index]
                                query = f'UPDATE "{table_name}" SET "{col_name}" = $1 WHERE id = $2'
                                await conn.execute(query, cell_data, current_row_id)
                    print(
                        f"Updated grid in {table_name} starting at ({start_row}, {start_col})"
                    )

                else:  # 1D list
                    if direction == "row":
                        set_clauses = []
                        args = []
                        for i, value in enumerate(data):
                            current_col_index = start_col - 1 + i
                            if current_col_index < len(column_names):
                                col_name = column_names[current_col_index]
                                set_clauses.append(f'"{col_name}" = ${i + 1}')
                                args.append(value)

                        if set_clauses:
                            args.append(start_row)
                            query = f'UPDATE "{table_name}" SET {", ".join(set_clauses)} WHERE id = ${len(args)}'
                            await conn.execute(query, *args)
                            print(f"Updated row in {table_name} at row id {start_row}")

                    elif direction == "column":
                        col_name = column_names[start_col - 1]
                        for i, value in enumerate(data):
                            current_row_id = start_row + i
                            query = f'UPDATE "{table_name}" SET "{col_name}" = $1 WHERE id = $2'
                            await conn.execute(query, value, current_row_id)
                        print(f"Updated column in {table_name} at column {start_col}")
