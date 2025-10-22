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

# === Startup banner ===
print("\033[32mStarting HER bot...\033[0m")

load_dotenv()
TOKEN = os.getenv("TOKEN")

config_path = Path(__file__).parent / "config.yml"
with open(config_path, "r") as f:
    config = yaml.safe_load(f)


class HER(commands.InteractionBot):
    def __init__(self, *args, **kwargs):
        if config.get("development_mode"):
            guild_id = config.get("testing_guild_id")
            if guild_id:
                kwargs["test_guilds"] = [guild_id]
                print(
                    f"\033[33m⚠ Dev mode: Instant command sync to guild {guild_id}\033[0m"
                )

        super().__init__(*args, **kwargs)
        self.launch_time = time.time()
        self.db = Database()
        self.config = config

    def load_all_cogs(self):
        print("\nLoading cogs...")
        cogs_dir = Path(__file__).parent / "Cogs"
        cogs = [
            f"Cogs.{f.stem}"
            for f in cogs_dir.iterdir()
            if f.suffix == ".py" and not f.name.startswith("__")
        ]

        success, fail = 0, 0
        for cog in cogs:
            try:
                self.load_extension(cog)
                print(f"\033[32m✓ Loaded {cog}\033[0m")
                success += 1
            except Exception as e:
                print(f"\033[31m✗ Failed to load {cog}: {e}\033[0m")
                fail += 1

        print(
            f"\033[32m✓ Successfully loaded {success}/{len(cogs)} cogs ({fail} failed)\033[0m\n"
        )

    async def setup_hook(self):
        try:
            print("Initializing services...")
            await self.db.connect()

            data_dir = Path(__file__).parent / "data"
            data_dir.mkdir(exist_ok=True)

            log_file = data_dir / "bot_logs.json"
            if not log_file.exists():
                log_file.write_text("[]")

        except Exception as e:
            print(f"\033[31m✗ Setup error: {e}\033[0m")
            await self.close()

    async def on_ready(self):
        startup_time = time.time() - self.launch_time
        await self.db.connect()
        db_status = "✅" if self.db.pool else "❌"

        print("\n" + "=" * 50)
        print(f"Connected as: {self.user}")
        print(f"Guilds: {len(self.guilds)}")
        print(f"Commands registered: {len(self.application_commands)}")

        if config.get("development_mode"):
            print(
                f"✓ Development mode (Test guild ID: {config.get('testing_guild_id')})"
            )
        else:
            print("✓ Production mode (Global command sync, may take up to 1 hour)")

        print("=" * 50)
        print(
            f"\033[32mStartup time: {startup_time:.2f}s | Database: {db_status}\033[0m\n"
        )
        print(f"\033[32m=== HER is ready! ===\033[0m\n")


async def shutdown(bot: HER):
    print("\n\033[33mShutting down bot...\033[0m")
    try:
        if bot.db and bot.db.pool:
            await bot.db.close()
            print("✓ Database closed")

        await bot.close()
        print("✓ Bot connection closed")
        print("\033[32mShutdown complete\033[0m\n")
    except Exception as e:
        print(f"\033[31m✗ Error during shutdown: {e}\033[0m")


async def main():
    intents = disnake.Intents.all()
    bot = HER(intents=intents)

    # Configure logger right after bot creation
    logger.configure(bot, config, logging_level=1)

    try:
        bot.load_all_cogs()
        await bot.start(TOKEN)
    except disnake.LoginFailure:
        print("\033[31m✗ Invalid TOKEN. Check your .env file.\033[0m")
    except KeyboardInterrupt:
        print("\n\033[33m⚠ Keyboard interrupt detected\033[0m")
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
