import asyncio
import os
import time
from pathlib import Path

import disnake
import yaml
from disnake.ext import commands
from dotenv import load_dotenv

from Modules.Database import Database
from Modules.Logger import logger

BANNER = "\033[32m hi\033[0m"
print(BANNER)

load_dotenv()
TOKEN = os.getenv("TOKEN")

config_path = Path(__file__).parent / "config.yml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)


class HER(commands.InteractionBot):
    def __init__(self, *args, **kwargs):
        if config.get("development_mode", False):
            testing_guild = config.get("testing_guild_id")
            if testing_guild:
                kwargs["test_guilds"] = [testing_guild]
                print(
                    f"\033[33m⚠  Dev mode: Commands sync instantly to guild {testing_guild}\033[0m"
                )

        super().__init__(*args, **kwargs)
        self.launch_time = time.time()
        self.db = Database()
        self.config = config

    def load_all_cogs(self):
        print("\nLoading cogs...")
        loaded_count = 0
        total_cogs = 0
        cogs_dir = Path(__file__).parent / "Cogs"

        for item in cogs_dir.iterdir():
            if (
                item.is_dir()
                or not item.name.endswith(".py")
                or item.name.startswith("__")
            ):
                continue

            cog_path = f"Cogs.{item.stem}"
            total_cogs += 1

            try:
                self.load_extension(cog_path)
                print(f"\033[32m✓ Loaded {cog_path}\033[0m")
                loaded_count += 1
            except Exception as e:
                print(f"\033[31m✗ Failed to load {cog_path}: {e}\033[0m")

        print(f"\033[32m✓ Loaded {loaded_count}/{total_cogs} cogs\033[0m\n")

    async def setup_hook(self):
        try:
            print("Initializing services...\n")
            await self.db.connect()

            data_dir = Path(__file__).parent / "data"
            data_dir.mkdir(exist_ok=True)

            log_file = data_dir / "bot_logs.json"
            if not log_file.exists():
                log_file.write_text("[]")

        except Exception as e:
            print(f"\033[31m✗ Failed during setup_hook: {e}\033[0m")
            await self.close()

    async def on_ready(self):
        startup_time = time.time() - self.launch_time
        await self.db.connect()
        db_status = "✅" if self.db.pool else "❌"

        print("\n" + "=" * 50)
        print("Command Sync Status:")
        print(f"Bot is in {len(self.guilds)} guild(s):")
        for guild in self.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")

        print(f"\nTotal commands registered: {len(self.application_commands)}")

        if config.get("development_mode", False):
            test_guild = config.get("testing_guild_id")
            print(f"✓ Development mode: Commands auto-sync to test guild {test_guild}")
            print("  → Commands appear INSTANTLY in test guilds")
        else:
            print("✓ Production mode: Commands are global")
            print("  → May take up to 1 hour to sync globally")
        print("=" * 50 + "\n")

        status_parts = [
            f"Connected as: {self.user}",
            f"Startup time: {startup_time:.2f}s",
            f"Database: {db_status}",
            f"Active cogs: {len(self.cogs)}",
            f"Commands registered: {len(self.application_commands)}",
        ]
        status = "\n".join(status_parts)
        print(f"\033[32m=== Bot Ready ===\n{status}\n===============\033[0m\n")


async def shutdown(bot):
    print("\n\033[33m=== Shutting down bot ===\033[0m")
    try:
        if bot.db and bot.db.pool:
            await bot.db.close()
            print("✓ Database connection closed")

        await bot.close()
        print("✓ Bot connection closed")
        print("\033[32m✓ Shutdown complete\033[0m\n")
    except Exception as e:
        print(f"\033[31m✗ Error during shutdown: {e}\033[0m")


async def main():
    intents = disnake.Intents.all()
    bot = HER(intents=intents)

    try:
        bot.load_all_cogs()
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n\033[33m⚠ Received keyboard interrupt\033[0m")
    except disnake.LoginError:
        print("\033[31m✗ Login failed. Check your TOKEN.\033[0m")
    except Exception as e:
        print(f"\033[31m✗ Bot crashed: {e}\033[0m")
        import traceback

        traceback.print_exc()
    finally:
        if not bot.is_closed():
            await shutdown(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[33m⚠ Forced shutdown\033[0m")
