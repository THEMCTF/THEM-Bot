# THEM?! Bot

A Discord bot made for THEM?!, providing CTF-focused features and management tools.

## Features

- CTF team management tools
- Challenge tracking
- Moderation utilities
- Configurable logging system

## Setup

1. **Environment Setup**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Copy `.env.example` to `.env` and fill in your bot token
   - Update `config.yml` with your server settings
   - Configure PostgreSQL connection details

3. **Database Setup**:
   ```bash
   createdb thembot
   ```

## Development

We use development tools for quality code:

- **Code Formatting**: `black`
  ```bash
  black .
  ```

- **Import Sorting**: `isort`
  ```bash
  isort .
  ```

- **Testing**: `pytest`
  ```bash
  pytest
  ```

## Configuration

All bot configuration is in `config.yml`:
```yaml
guild_id: YOUR_GUILD_ID
logging_channel: LOGGING_CHANNEL_ID
enable_channel_logging: true
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run `black` and `isort` on your changes
4. Submit a pull request

## (basic) File Structure

```
bot/
├── Cogs/           # Command modules
├── Modules/        # Core functionality
├── config.yml     # Configuration
├── main.py        # Bot entry point
└── requirements.txt
```

## License

MIT License - See LICENSE file for details

README is written by AI, contact @Starry0Wolf for more info.